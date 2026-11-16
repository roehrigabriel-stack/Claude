#!/usr/bin/env python3
"""Bugatti Tourbillon showcase film: fully synthesised soundtrack.

Usage:  python3 audio/make_music.py [--timeline anim/timeline.json] [--out out/audio/soundtrack.wav]

Everything (tempo, section layout, event sounds) is derived at run time from the
timeline.  Python 3 stdlib + numpy only.  Deterministic (fixed seeds).
Key: D minor, progression i - VI - iv - V (Dm Bb Gm A), final resolution on Dm.
"""
import argparse
import json
import os
import sys
import time
import wave

import numpy as np

SR = 48000
TWO_PI = 2.0 * np.pi
np.seterr(over="ignore", under="ignore", divide="ignore", invalid="ignore")


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------
def midi(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def tvec(n):
    return np.arange(n) / SR


def boxsmooth(x, width):
    """moving average (two passes -> triangular), width in samples"""
    w = max(int(width), 1)
    if w <= 1:
        return x
    for _ in range(2):
        pad = np.concatenate([np.full(w // 2, x[0]), x, np.full(w - w // 2, x[-1])])
        cs = np.cumsum(np.concatenate([[0.0], pad]))
        x = (cs[w:] - cs[:-w])[: len(x)] / w
    return x


def edges(x, a=0.002, r=0.01):
    """attack / release ramps so that nothing clicks"""
    n = len(x)
    na = min(int(a * SR), n // 2)
    nr = min(int(r * SR), n // 2)
    y = x.copy()
    if na > 0:
        y[:na] *= smoothstep(np.arange(na) / na)
    if nr > 0:
        y[n - nr:] *= smoothstep(np.arange(nr, 0, -1) / nr)
    return y


# ----------------------------------------------------------------------------
# filters (FFT based, zero phase, no scipy)
# ----------------------------------------------------------------------------
def _mag(kind, f, fc, order, q):
    f = np.maximum(f, 1e-3)
    if kind == "lp":
        r = f / fc
        h = 1.0 / np.sqrt(1.0 + r ** (2 * order))
        if q > 0:
            h = h * (1.0 + q * np.exp(-0.5 * (np.log(np.maximum(r, 1e-9)) / 0.28) ** 2))
        return h
    if kind == "hp":
        r = fc / f
        return 1.0 / np.sqrt(1.0 + r ** (2 * order))
    if kind == "bp":
        return 1.0 / np.sqrt(1.0 + (q * (f / fc - fc / f)) ** 2)
    raise ValueError(kind)


def sfilter(x, kind, fc, order=2, q=0.0):
    """static filter over the whole signal (1-D or 2-D)"""
    if x.ndim == 2:
        return np.stack([sfilter(c, kind, fc, order, q) for c in x])
    n = len(x)
    nf = 1 << int(np.ceil(np.log2(n + 8192)))
    X = np.fft.rfft(x, nf)
    f = np.fft.rfftfreq(nf, 1.0 / SR)
    return np.fft.irfft(X * _mag(kind, f, fc, order, q), nf)[:n]


def tvfilter(x, fc, kind="lp", order=2, q=0.0, hop=1024):
    """time varying filter: overlap-add of Hann windowed frames, each frame
    multiplied by a magnitude response whose cutoff follows fc(t)."""
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, dtype=float), (n,)) if np.ndim(fc) == 0 else np.asarray(fc, dtype=float)
    L = 2 * hop
    nf = 4 * hop
    m = n // hop + 2
    xp = np.zeros((m + 1) * hop + L)
    xp[hop:hop + n] = x
    win = 0.5 - 0.5 * np.cos(TWO_PI * np.arange(L) / L)
    idx = np.arange(m)[:, None] * hop + np.arange(L)[None, :]
    spec = np.fft.rfft(xp[idx] * win, nf, axis=1)
    cen = np.clip(np.arange(m) * hop, 0, n - 1)
    fcc = fc[cen][:, None]
    f = np.fft.rfftfreq(nf, 1.0 / SR)[None, :]
    h = _mag(kind, f, fcc, order, q)
    fr = np.fft.irfft(spec * h, nf, axis=1)[:, :L]
    out = np.zeros_like(xp)
    for k in range(2):  # overlap add in two interleaved passes (vectorised)
        sel = fr[k::2]
        base = np.arange(k, m, 2) * hop
        # frames of the same parity do not overlap each other
        o = (base[:, None] + np.arange(L)[None, :])
        out[o.ravel()] += sel.ravel()
    return out[hop:hop + n]


def fftconv(x, ir):
    n = len(x) + len(ir)
    nf = 1 << int(np.ceil(np.log2(n)))
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(ir, nf), nf)[: len(x)]


# ----------------------------------------------------------------------------
# oscillators
# ----------------------------------------------------------------------------
def saw_blep(freq, phase0=0.0):
    """polyBLEP band limited saw; freq scalar-or-array (Hz) of length n"""
    inc = np.asarray(freq, dtype=float) / SR
    ph = (phase0 + np.cumsum(inc)) % 1.0
    y = 2.0 * ph - 1.0
    dt = np.maximum(inc, 1e-9)
    m1 = ph < dt
    x = ph[m1] / dt[m1] if np.ndim(dt) else ph[m1] / dt
    y[m1] -= (2 * x - x * x - 1.0)
    m2 = ph > 1.0 - dt
    d2 = dt[m2] if np.ndim(dt) else dt
    x = (ph[m2] - 1.0) / d2
    y[m2] -= (x * x + 2 * x + 1.0)
    return y


# ----------------------------------------------------------------------------
# loudness / limiter
# ----------------------------------------------------------------------------
def _kweight(x):
    """exact BS.1770 K-weighting at 48 kHz applied through the FFT"""
    n = len(x)
    nf = 1 << int(np.ceil(np.log2(n + 16384)))
    w = TWO_PI * np.fft.rfftfreq(nf, 1.0 / SR) / SR
    z = np.exp(-1j * w)

    def bq(b, a):
        return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)

    h = bq([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
    h = h * bq([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])
    return np.fft.irfft(np.fft.rfft(x, nf) * h, nf)[:n]


def lufs_blocks(y):
    """returns (block_loudness array, block_times) for 400 ms blocks, 100 ms hop"""
    ms = sum(np.square(_kweight(c)) for c in y)
    cs = np.concatenate([[0.0], np.cumsum(ms)])
    bs, hp = int(0.4 * SR), int(0.1 * SR)
    starts = np.arange(0, max(len(ms) - bs, 1), hp)
    e = (cs[starts + bs] - cs[starts]) / bs
    return -0.691 + 10 * np.log10(np.maximum(e, 1e-12)), starts / SR


def integrated_lufs(y):
    l, _ = lufs_blocks(y)
    g = l[l > -70]
    if len(g) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(10 ** ((g + 0.691) / 10))) - 10
    g2 = l[l > rel]
    return -0.691 + 10 * np.log10(np.mean(10 ** ((g2 + 0.691) / 10)))


def true_peak(y):
    n = y.shape[1]
    nf = 1 << int(np.ceil(np.log2(n * 4)))
    pk = 0.0
    for c in y:
        X = np.fft.rfft(c, n)
        Xp = np.zeros(n * 4 // 2 + 1, dtype=complex)
        Xp[: len(X)] = X
        up = np.fft.irfft(Xp, n * 4) * 4
        pk = max(pk, np.max(np.abs(up)))
    return pk


def limiter(y, ceil, look=0.0035):
    """lookahead peak limiter (min-filter + smoothing of the gain curve)"""
    pk = np.max(np.abs(y), axis=0)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-12))
    w = int(look * SR) * 2 + 1
    if need.min() >= 1.0:
        return y
    pad = np.concatenate([np.ones(w // 2), need, np.ones(w // 2)])
    from numpy.lib.stride_tricks import sliding_window_view
    # only compute the sliding minimum where needed
    mn = np.ones(len(need))
    idx = np.where(need < 1.0)[0]
    lo = np.clip(idx - w // 2, 0, len(need) - 1)
    # spread each limited sample over +-w/2 (min filter by scatter)
    win = sliding_window_view(pad, w)
    sel = np.unique(np.clip(np.concatenate([idx + k for k in range(-(w // 2), w // 2 + 1, 24)]), 0, len(need) - 1))
    mn[sel] = win[sel].min(axis=1)
    # fill gaps from the coarse scatter
    ker = np.hanning(w)
    ker /= ker.sum()
    g = np.convolve(np.pad(mn, (w, w), constant_values=1.0), ker, mode="same")[w:-w]
    # the smoothing may be slightly late for narrow peaks, guard with a second min
    g = np.minimum(g, 1.0)
    out = y * g
    over = np.max(np.abs(out), axis=0)
    resid = np.minimum(1.0, ceil / np.maximum(over, 1e-12))
    return out * resid


# ----------------------------------------------------------------------------
# main renderer
# ----------------------------------------------------------------------------
class Film:
    def __init__(self, tl):
        self.tl = tl
        self.dur = float(tl["duration"])
        self.N = int(round(self.dur * SR))
        self.T = tvec(self.N)
        self.events = sorted(tl.get("events", []), key=lambda e: e["t"])
        self.secs = [dict(name=s["name"], t0=float(s["t0"]), t1=float(s["t1"])) for s in tl["sections"]]
        self.rng_seed = 20260101
        self.setup()

    # ---------------- timeline interpretation -----------------
    def ev(self, typ):
        return [e for e in self.events if e["type"] == typ]

    def setup(self):
        dur = self.dur
        ig = self.ev("ignition")
        isec = [s for s in self.secs if s["name"] == "ignition"]
        if ig:
            self.ign = float(ig[0]["t"])
        elif isec:
            self.ign = isec[0]["t0"] + 0.5 * (isec[0]["t1"] - isec[0]["t0"])
        else:
            self.ign = 0.34 * dur
        # effective sections: assembly ends at the ignition hit, ignition section begins there
        S = []
        for s in self.secs:
            s = dict(s)
            if s["name"] == "assembly":
                s["t1"] = max(s["t0"] + 0.5, self.ign)
            if s["name"] == "ignition":
                s["t0"] = self.ign
            S.append(s)
        self.S = S
        # silence gap before the ignition hit
        lands_before = [e["t"] for e in self.ev("land") if e["t"] < self.ign - 0.05]
        gs = self.ign - 0.42
        if lands_before and lands_before[-1] > self.ign - 1.0:
            gs = max(gs, lands_before[-1] + 0.14)
        self.gap_start = min(gs, self.ign - 0.22)
        # final landing (doors shut)
        dc = self.ev("door_close")
        lands = [e for e in self.ev("land")]
        fin = None
        if dc:
            cand = [e for e in lands if e["t"] > dc[0]["t"]]
            if cand:
                fin = cand[-1]["t"]
        if fin is None and lands:
            fin = lands[-1]["t"] if lands[-1]["t"] > 0.75 * dur else None
        self.t_final = fin if fin is not None else 0.92 * dur
        fo = self.ev("fade_out")
        self.t_fade = float(fo[0]["t"]) if fo else dur - 1.0
        self.choose_tempo()

    def choose_tempo(self):
        starts = [s["t0"] for s in self.S if s["t0"] > 0.01]
        ign = self.ign
        best = None
        for bpm in np.arange(80.0, 124.01, 0.25):
            b = 60.0 / bpm
            bar = 4 * b
            cost = 0.0
            for s in starts:
                db_ = abs(((s - ign) / b + 0.5) % 1.0 - 0.5) * b
                dbar = abs(((s - ign) / bar + 0.5) % 1.0 - 0.5) * bar
                cost += 0.75 * db_ + 0.25 * dbar
            cost += 0.006 * (max(0.0, bpm - 110.0) + max(0.0, 92.0 - bpm))  # prefer a confident mid tempo
            if best is None or cost < best[0]:
                best = (cost, bpm)
        self.bpm = best[1]
        self.tempo_cost = best[0] / max(len(starts), 1)
        self.beat = 60.0 / self.bpm
        self.bar = 4 * self.beat
        self.s16 = self.beat / 4
        self.t_down = ign  # ignition is on a downbeat

    # ---------------- sections -----------------
    ALIAS = {}

    def prof(self, name):
        known = ("intro", "assembly", "ignition", "hero_front", "profile", "rear", "doors", "interior", "finale")
        return name if name in known else "hero_front"

    def sec_at(self, t, snapped=False):
        S = self.S
        for s in reversed(S):
            t0 = self.snap(s["t0"]) if snapped else s["t0"]
            if t >= t0 - 1e-9:
                return s
        return S[0]

    def snap(self, t):
        if t <= 0.01:
            return t
        k = round((t - self.t_down) / self.beat)
        tb = self.t_down + k * self.beat
        if abs(tb - t) <= 0.12:
            return tb
        k = round((t - self.t_down) / self.s16)
        return self.t_down + k * self.s16

    def curve(self, table, smooth=0.3):
        arr = np.zeros(self.N)
        for s in self.S:
            a, b = table.get(self.prof(s["name"]), (0.0, 0.0))
            i0 = int(round(s["t0"] * SR))
            i1 = min(int(round(s["t1"] * SR)), self.N)
            if i1 > i0:
                arr[i0:i1] = a + (b - a) * np.arange(i1 - i0) / (i1 - i0)
        last = self.S[-1]
        arr[int(round(last["t1"] * SR)):] = table.get(self.prof(last["name"]), (0, 0))[1]
        return boxsmooth(arr, smooth * SR)

    # ---------------- buses -----------------
    def new_bus(self):
        z = lambda: np.zeros((2, self.N))
        return {"dry": z(), "hall": z(), "room": z()}

    def put(self, bus, t, sig, pan=0.0, gain=1.0, hall=0.0, room=0.0):
        i0 = int(round(t * SR))
        n = sig.shape[-1]
        a = max(0, -i0)
        b = min(n, self.N - i0)
        if b <= a:
            return
        seg = sig[..., a:b] * gain
        sl = slice(i0 + a, i0 + b)
        if sig.ndim == 1:
            th = (pan + 1.0) * np.pi / 4.0
            gl, gr = np.cos(th), np.sin(th)
            st = np.stack([seg * gl, seg * gr])
        else:
            st = seg
        bus["dry"][:, sl] += st
        if hall:
            bus["hall"][:, sl] += st * hall
        if room:
            bus["room"][:, sl] += st * room

    def addtrack(self, bus, tr, gain=1.0, hall=0.0, room=0.0, pan=0.0):
        if tr.ndim == 1:
            th = (pan + 1.0) * np.pi / 4.0
            tr = np.stack([tr * np.cos(th), tr * np.sin(th)])
        bus["dry"] += tr * gain
        if hall:
            bus["hall"] += tr * (gain * hall)
        if room:
            bus["room"] += tr * (gain * room)


# ----------------------------------------------------------------------------
# sound design templates
# ----------------------------------------------------------------------------
def hp_noise(rng, n, k=1):
    x = rng.standard_normal(n)
    for _ in range(k):
        x = np.diff(x, prepend=0.0)
    return x


def tpl_kick(vel=1.0):
    n = int(0.55 * SR)
    t = tvec(n)
    f = 46.0 + 105.0 * np.exp(-t / 0.028)
    ph = TWO_PI * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.17)
    rng = np.random.default_rng(1)
    click = sfilter(rng.standard_normal(n), "lp", 3500, 2) * np.exp(-t / 0.0018)
    y = np.tanh(1.7 * body) * 0.9 + 0.22 * click
    y = edges(y, 0.0008, 0.02)
    return y * vel


def tpl_thump(freq, vel=1.0, decay=0.16):
    n = int(0.5 * SR)
    t = tvec(n)
    f = freq * (1.0 + 0.9 * np.exp(-t / 0.02))
    ph = TWO_PI * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / decay)
    y += 0.25 * np.sin(2 * ph) * np.exp(-t / (decay * 0.5))
    return edges(np.tanh(1.3 * y), 0.002, 0.03) * vel


def tpl_tick(kind, vel, rng):
    """watch-movement tick: metallic ring + tiny noise burst"""
    n = int(0.09 * SR)
    t = tvec(n)
    if kind == 0:
        fr, am = (3340.0, 5120.0, 7350.0), (1.0, 0.55, 0.25)
    elif kind == 1:
        fr, am = (2480.0, 3890.0, 6010.0), (1.0, 0.5, 0.2)
    else:  # soft hat-like
        fr, am = (4300.0, 6400.0), (0.5, 0.3)
    y = sum(a * np.sin(TWO_PI * f * t + rng.uniform(0, 6.28)) * np.exp(-t / (0.011 + 0.004 * i)) for i, (f, a) in enumerate(zip(fr, am)))
    y = y + 0.9 * hp_noise(rng, n, 1) * np.exp(-t / 0.0022) * 0.35
    y = edges(y, 0.0004, 0.01)
    return y * vel * 0.5


def tpl_hat(vel, open_=False, rng=None):
    rng = rng or np.random.default_rng(7)
    n = int((0.22 if open_ else 0.07) * SR)
    t = tvec(n)
    x = hp_noise(rng, n, 2)
    x = sfilter(x, "lp", 11000, 2)
    y = x * np.exp(-t / (0.09 if open_ else 0.017))
    return edges(y, 0.0005, 0.01) * vel * 0.18


def tpl_snare(vel, rng):
    n = int(0.3 * SR)
    t = tvec(n)
    nz = sfilter(hp_noise(rng, n, 1), "bp", 2400, 1, q=0.7) * np.exp(-t / 0.075)
    tone = np.sin(TWO_PI * (170 + 70 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.06)
    y = 0.55 * nz + 0.5 * tone
    return edges(np.tanh(1.4 * y), 0.0007, 0.02) * vel * 0.8


def tpl_clunk(weight, rng):
    """tight mechanical latch impact: low thump + bright click + metallic ring"""
    w = float(np.clip(weight, 0.1, 1.2))
    n = int(0.6 * SR)
    t = tvec(n)
    f = (52.0 + 28.0 * (1.0 - min(w, 1.0))) + 85.0 * np.exp(-t / 0.022)
    ph = TWO_PI * np.cumsum(f) / SR
    low = np.sin(ph) * np.exp(-t / (0.055 + 0.075 * w)) * (0.45 + 0.65 * w)
    shell = np.sin(TWO_PI * rng.uniform(150, 210) * t) * np.exp(-t / 0.028) * 0.3 * w
    click = sfilter(hp_noise(rng, n, 1), "hp", 1800, 2) * np.exp(-t / 0.0016) * 0.5
    ring = np.zeros(n)
    for f0 in rng.choice([1870.0, 2540.0, 3110.0, 3980.0, 4720.0, 5650.0], 3, replace=False):
        ring += rng.uniform(0.12, 0.22) * np.sin(TWO_PI * f0 * t + rng.uniform(0, 6.28)) * np.exp(-t / rng.uniform(0.03, 0.075))
    y = low + shell + click + ring * (0.6 + 0.5 * w)
    # latch: second, smaller click
    d = int(rng.uniform(0.018, 0.028) * SR)
    y[d:] += 0.35 * (sfilter(hp_noise(rng, n - d, 1), "hp", 2500, 2) * np.exp(-tvec(n - d) / 0.0012)) * 0.5
    y[d:] += 0.12 * np.sin(TWO_PI * 3300 * tvec(n - d)) * np.exp(-tvec(n - d) / 0.02)
    y = np.tanh(1.2 * y)
    return edges(y, 0.0006, 0.05)


def tpl_thud(vel=1.0):
    """the final doors-shut thud: deep, satisfying"""
    n = int(1.4 * SR)
    t = tvec(n)
    f = 38.0 + 62.0 * np.exp(-t / 0.05)
    ph = TWO_PI * np.cumsum(f) / SR
    low = np.sin(ph) * np.exp(-t / 0.42)
    mid = np.sin(TWO_PI * 96 * t + 0.3) * np.exp(-t / 0.09) * 0.4
    rng = np.random.default_rng(99)
    body = sfilter(rng.standard_normal(n), "lp", 260, 2) * np.exp(-t / 0.2) * 1.2
    click = sfilter(hp_noise(rng, n, 1), "bp", 2200, 1, q=0.8) * np.exp(-t / 0.004) * 0.35
    y = np.tanh(1.3 * (low + mid + body + click))
    return edges(y, 0.001, 0.15) * vel


def tpl_bell(f, dur, vel=1.0, bright=1.0, kind="bell"):
    n = int(dur * SR)
    t = tvec(n)
    if kind == "bell":
        env = np.exp(-t / (0.55 * dur / 1.0 + 0.2)) * smoothstep(t / 0.003)
        idx = 2.0 * bright * np.exp(-t / 0.22)
        y = np.sin(TWO_PI * f * t + idx * np.sin(TWO_PI * f * 2.0 * t))
        y += 0.25 * bright * np.sin(TWO_PI * f * 3.0 * t + 0.4) * np.exp(-t / 0.1)
        y += 0.18 * np.sin(TWO_PI * f * 0.5 * t) * np.exp(-t / 0.3)
        y *= env
    else:  # glassy pluck
        parts = [(1.0, 1.0, 0.9), (2.756, 0.45, 0.45), (5.404, 0.22, 0.25), (8.93, 0.1, 0.15)]
        y = np.zeros(n)
        for r, a, d in parts:
            if f * r < 11000:
                y += a * np.sin(TWO_PI * f * r * t + r) * np.exp(-t / (d * dur * 0.5 + 0.05))
        y *= smoothstep(t / 0.002)
    return edges(y, 0.001, min(0.08, dur * 0.3)) * vel * 0.45


def tpl_servo(dur, f0, f1, rng, level=1.0, ease=True, tail=0.15):
    n = int((dur + tail) * SR)
    t = tvec(n)
    p = np.clip(t / dur, 0, 1)
    p = smoothstep(p) if ease else p
    f = f0 + (f1 - f0) * p
    ph = TWO_PI * np.cumsum(f) / SR
    y = np.zeros(n)
    for k, a in zip(range(1, 10), (1.0, 0.55, 0.7, 0.3, 0.45, 0.2, 0.28, 0.12, 0.15)):
        y += a / k ** 0.5 * np.sin(k * ph + k)
    y *= 1.0 + 0.18 * np.sin(TWO_PI * (f / 9.0) * t)  # motor flutter
    nz = sfilter(rng.standard_normal(n), "bp", 1800, 1, q=1.2)
    y = y * 0.5 + nz * 0.35
    y = sfilter(y, "lp", 5200, 2)
    env = smoothstep(t / (0.18 * dur)) * (1 - smoothstep((t - dur) / tail))
    env *= 0.55 + 0.45 * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.5
    return edges(y * env, 0.005, 0.03) * level * 0.45


def tpl_whoosh(dur, rng, vel=1.0):
    n = int((dur + 0.07) * SR)
    t = tvec(n)
    p = np.clip(t / dur, 0, 1)
    nz = rng.standard_normal(n)
    fc = 350.0 * (4800.0 / 350.0) ** (p ** 1.4)
    y = tvfilter(nz, fc, "bp", q=1.3, hop=512)
    env = np.sin(0.5 * np.pi * p) ** 2.4
    env = np.where(t <= dur, env, np.cos(0.5 * np.pi * np.clip((t - dur) / 0.06, 0, 1)) ** 2)
    return edges(y * env, 0.01, 0.01) * vel


def tpl_chime(f, dur, vel=1.0):
    n = int(dur * SR)
    t = tvec(n)
    y = np.zeros(n)
    for r, a, d in [(1.0, 1.0, 1.0), (2.756, 0.5, 0.55), (5.404, 0.28, 0.3), (8.93, 0.14, 0.18)]:
        if f * r < 12000:
            y += a * np.sin(TWO_PI * f * r * t) * np.exp(-t / (0.5 * dur * d + 0.04))
    return edges(y * smoothstep(t / 0.0015), 0.0015, 0.1) * vel * 0.35


# ----------------------------------------------------------------------------
# harmony
# ----------------------------------------------------------------------------
CHORDS = {
    "Dm": dict(root=38, pad=[50, 57, 62, 65, 69], bass=38, tones=[62, 65, 69, 74]),
    "Bb": dict(root=34, pad=[46, 58, 62, 65, 70], bass=34, tones=[58, 62, 65, 70]),
    "Gm": dict(root=31, pad=[43, 55, 58, 62, 67], bass=31, tones=[55, 58, 62, 67]),
    "A": dict(root=33, pad=[45, 57, 61, 64, 69], bass=33, tones=[57, 61, 64, 69]),
}
MOTIF = {  # (step in 16ths, midi, length in 16ths)
    "Dm": [(0, 69, 6), (6, 74, 2), (8, 77, 8)],
    "Bb": [(0, 74, 6), (6, 72, 2), (8, 70, 8)],
    "Gm": [(0, 70, 6), (6, 74, 2), (8, 79, 8)],
    "A": [(0, 76, 6), (6, 73, 2), (8, 69, 8)],
}
PROG = {
    "default": ["Dm", "Bb", "Gm", "A"],
    "doors": ["Bb", "Gm", "Dm", "A"],
}

# layer levels (start, end) per section profile
LV = {
    "drone": {"intro": (0.0, 0.9), "assembly": (0.9, 1.0), "ignition": (0.5, 0.25), "hero_front": (0.2, 0.2), "profile": (0.2, 0.2), "rear": (0.2, 0.2), "doors": (0.22, 0.18), "interior": (0.12, 0.12), "finale": (0.2, 0.3)},
    "shimmer": {"intro": (0.1, 0.8), "assembly": (0.5, 0.9), "ignition": (0.7, 0.4), "hero_front": (0.25, 0.3), "profile": (0.3, 0.3), "rear": (0.35, 0.4), "doors": (0.55, 0.6), "interior": (0.75, 0.75), "finale": (0.4, 0.45)},
    "pad": {"assembly": (0.08, 0.8), "ignition": (0.9, 0.55), "hero_front": (0.5, 0.55), "profile": (0.58, 0.62), "rear": (0.65, 0.75), "doors": (0.55, 0.6), "interior": (0.24, 0.24), "finale": (0.7, 0.8)},
    "padfc": {"assembly": (260, 3600), "ignition": (6000, 2600), "hero_front": (1700, 2100), "profile": (2100, 2600), "rear": (2600, 3500), "doors": (3000, 3600), "interior": (1500, 1500), "finale": (2800, 3200)},
    "lead": {"hero_front": (0.55, 0.65), "profile": (0.75, 0.8), "rear": (0.85, 1.0), "doors": (0.5, 0.55), "finale": (0.95, 1.0)},
    "arp": {"profile": (0.25, 0.3), "rear": (0.45, 0.5), "doors": (0.65, 0.7), "interior": (0.75, 0.75), "finale": (0.35, 0.4)},
    "bass": {"hero_front": (0.8, 0.85), "profile": (0.9, 0.9), "rear": (1.0, 1.0), "doors": (0.35, 0.3), "interior": (0.08, 0.08), "finale": (1.0, 0.95)},
    "kick": {"hero_front": (0.85, 0.9), "profile": (0.95, 0.95), "rear": (1.0, 1.0), "doors": (0.0, 0.0), "finale": (1.0, 1.0)},
    "tick": {"assembly": (0.25, 1.0), "ignition": (0.0, 0.0), "hero_front": (0.45, 0.5), "profile": (0.55, 0.6), "rear": (0.65, 0.7), "doors": (0.5, 0.55), "interior": (1.0, 1.0), "finale": (0.6, 0.6)},
}


def render(tl_path, out_path):
    t_start = time.time()
    with open(tl_path) as fh:
        tl = json.load(fh)
    F = Film(tl)
    N, T, dur = F.N, F.T, F.dur
    rng = np.random.default_rng(F.rng_seed)
    M = F.new_bus()  # music bus, gated before the ignition hit
    X = F.new_bus()  # ungated bus (ignition, engine, final)
    log = lambda *a: print("[%5.1fs]" % (time.time() - t_start), *a, flush=True)
    log("duration %.2f s, bpm %.2f (beat %.4f s, bar %.4f s), mean section offset %.3f s" % (dur, F.bpm, F.beat, F.bar, F.tempo_cost))

    ign, beat, bar, s16, t_down = F.ign, F.beat, F.bar, F.s16, F.t_down
    gs = F.gap_start

    # ---- gate (near silence before the ignition) ----
    gate = np.ones(N)
    i0, i1 = int(gs * SR), int((ign - 0.004) * SR)
    ramp = int(0.05 * SR)
    gate[i0:i1] = 0.0
    if i0 + ramp <= i1:
        gate[i0:i0 + ramp] = 1 - smoothstep(np.arange(ramp) / ramp)
    gate[i1:int(ign * SR)] = 0.0
    gate[: int(ign * SR)][i0:] = gate[: int(ign * SR)][i0:] * 0.0 + gate[: int(ign * SR)][i0:]
    r2 = int(0.004 * SR)
    gate[i1:i1 + r2] = smoothstep(np.arange(r2) / r2) if False else gate[i1:i1 + r2]
    gate = np.maximum(gate, 0.0)
    gate[int(ign * SR):] = 1.0

    # ---- chords per bar ----
    kmin = int(np.floor((0 - t_down) / bar)) - 1
    kmax = int(np.ceil((dur - t_down) / bar)) + 1
    bar_sec = {}
    for k in range(kmin, kmax + 1):
        tc = t_down + (k + 0.5) * bar
        bar_sec[k] = F.sec_at(min(max(tc, 0.0), dur - 1e-6))["name"]
    k_ign = 0
    k_fin = int(np.ceil((F.t_final - 0.25 * beat - t_down) / bar)) - 1
    chord_of = {}
    first_of = {}
    for k in range(kmin, kmax + 1):
        nm = bar_sec[k]
        if nm not in first_of or first_of[nm] > k:
            first_of[nm] = k
    for k in range(kmin, kmax + 1):
        nm = F.prof(bar_sec[k])
        prog = PROG.get(nm, PROG["default"])
        L = len(prog)
        if nm == "assembly":
            idx = (L - 1) - ((k_ign - 1 - k) % L)
        elif nm == "finale" and k <= k_fin:
            idx = (L - 1) - ((k_fin - k) % L)
        else:
            idx = (k - first_of[bar_sec[k]]) % L
        chord_of[k] = prog[idx]
    chord_of[k_fin + 1] = "Dm"

    def bar_of(t):
        return int(np.floor((t - t_down) / bar + 1e-9))

    # ---- step grid ----
    s_lo = int(np.floor((0 - t_down) / s16))
    s_hi = int(np.ceil((dur - t_down) / s16))
    steps = []
    for s in range(s_lo, s_hi + 1):
        t = t_down + s * s16
        if t < 0 or t >= dur:
            continue
        steps.append((s, t, s % 16, F.sec_at(t, snapped=True)))
    # active groove region ends a hair before the final thud
    t_groove_end = F.t_final - 0.02

    lv = {k: F.curve(v) for k, v in LV.items() if k != "padfc"}
    padfc = F.curve(LV["padfc"], smooth=0.5)
    sec_p = lambda s, t: float(np.clip((t - s["t0"]) / max(s["t1"] - s["t0"], 1e-6), 0, 1))

    # ---- hits scheduling (kicks / thumps) for sidechain ----
    kick_hits = []  # (t, vel)
    thump_hits = []
    for s, t, st, sec in steps:
        nm = F.prof(sec["name"])
        if t >= t_groove_end or (gs <= t < ign):
            continue
        vel_l = lv["kick"][min(int(t * SR), N - 1)]
        if nm in ("hero_front", "profile", "rear", "finale"):
            pat = {"hero_front": {0: 1.0, 8: 0.95, 11: 0.5},
                   "profile": {0: 1.0, 4: 0.85, 8: 0.95, 12: 0.85, 14: 0.4},
                   "rear": {0: 1.0, 4: 0.9, 8: 1.0, 12: 0.9, 6: 0.45, 14: 0.5},
                   "finale": {0: 1.0, 4: 0.9, 8: 1.0, 12: 0.9, 14: 0.45}}[nm]
            if st in pat:
                kick_hits.append((t, pat[st] * vel_l))
        if nm == "doors" and st == 0:
            thump_hits.append((t, 0.35, midi(CHORDS[chord_of[bar_of(t)]]["root"] + 12)))
        if nm == "assembly":
            p = sec_p(F.sec_at(t), t)
            p = float(np.clip((t - F.S[[x["name"] for x in F.S].index("assembly")]["t0"]) / max(gs - F.S[[x["name"] for x in F.S].index("assembly")]["t0"], 1e-6), 0, 1)) if any(x["name"] == "assembly" for x in F.S) else p
            if p < 0.3:
                on = st % 4 == 0
            elif p < 0.55:
                on = st % 2 == 0
            elif p < 0.8:
                on = st % 2 == 0 or st % 4 == 3
            else:
                on = True
            if on and t >= F.S[[x["name"] for x in F.S].index("assembly")]["t0"] + 0.25 * beat:
                acc = 1.0 if st % 4 == 0 else (0.6 if st % 2 == 0 else 0.4)
                thump_hits.append((t, (0.3 + 0.7 * p) * acc, midi(CHORDS[chord_of[bar_of(t)]]["root"] + 12)))

    duck = np.ones(N)

    def add_duck(t, depth, rel=0.13):
        i0 = int(t * SR)
        n = int(min(0.6, 5 * rel) * SR)
        if i0 >= N:
            return
        n = min(n, N - i0)
        tt = np.arange(n) / SR
        c = 1.0 - depth * np.exp(-tt / rel) * (1 - np.exp(-tt / 0.003))
        duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], c)

    for t, v in kick_hits:
        add_duck(t, 0.5 * min(v, 1.0))
    for t, v, f in thump_hits:
        add_duck(t, 0.18 * min(v, 1.0), 0.09)

    # ---------------------------------------------------------------- layers
    # 1. sub drone (D1 + D2, slow beating)
    log("drone / shimmer")
    f0 = float(midi(26))
    trem = 1.0 + 0.12 * np.sin(TWO_PI * 0.11 * T)
    drone = np.sin(TWO_PI * f0 * T) + 0.55 * np.sin(TWO_PI * f0 * 2 * T + 0.5) + 0.3 * np.sin(TWO_PI * (f0 * 4 + 0.27) * T)
    drone2 = 0.45 * np.sin(TWO_PI * (f0 * 2 + 0.31) * T)
    drone = np.tanh(1.4 * (drone + drone2) * trem) * 0.5
    drone = sfilter(drone, "lp", 420, 2)
    drone *= lv["drone"] * (0.6 + 0.4 * duck)
    F.addtrack(M, drone, gain=0.33, hall=0.1)

    # 2. airy shimmer (high sines with slow amplitude drift + soft noise)
    srng = np.random.default_rng(11)
    sh = np.zeros((2, N))
    for m_, a in zip((74, 81, 86, 89, 93, 98), (0.9, 0.8, 0.7, 0.5, 0.45, 0.3)):
        for ch in range(2):
            f = float(midi(m_)) * (1 + srng.uniform(-0.0012, 0.0012))
            lfo = 0.5 + 0.5 * np.sin(TWO_PI * srng.uniform(0.05, 0.22) * T + srng.uniform(0, 6.28))
            vib = 1.0 + 0.0008 * np.sin(TWO_PI * srng.uniform(0.2, 0.5) * T)
            sh[ch] += a * lfo ** 1.6 * np.sin(TWO_PI * f * np.cumsum(vib) / SR + srng.uniform(0, 6.28))
    air = srng.standard_normal((2, N))
    air = sfilter(air, "bp", 8200, 1, q=0.8)
    airlfo = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(TWO_PI * 0.13 * T))
    sh = (sh * 0.06 + air * 0.035 * airlfo) * lv["shimmer"] * (0.7 + 0.3 * duck)
    F.addtrack(M, sh, gain=1.0, hall=0.8)

    # 3. light sweep
    for e in F.ev("light_sweep"):
        t = e["t"]
        d = 1.9
        n = int(d * SR)
        tt = tvec(n)
        p = tt / d
        env = np.sin(np.pi * p) ** 2
        fc = 260.0 * (7000.0 / 260.0) ** (p ** 1.2)
        nz = tvfilter(rng.standard_normal(n), fc, "bp", q=1.8, hop=512)
        tone = 0.5 * np.sin(TWO_PI * midi(86) * tt) + 0.35 * np.sin(TWO_PI * midi(93) * tt + 1) + 0.3 * np.sin(TWO_PI * midi(81) * tt)
        y = (nz * 1.1 + tone * 0.08) * env
        y = edges(y, 0.05, 0.1)
        pan = -0.85 + 1.7 * smoothstep(p)
        th = (pan + 1) * np.pi / 4
        st = np.stack([y * np.cos(th), y * np.sin(th)])
        F.put(M, t, st, gain=0.55, hall=0.7)

    # 4. heartbeat / thumps
    log("pulse, ostinato, ticks")
    for t, v, f in thump_hits:
        F.put(M, t, tpl_thump(float(f) * 0.5 if f > 90 else float(f), 1.0), 0.0, gain=0.38 * v, room=0.05)

    # 5. ostinato (saw bass pluck) in the assembly, tightens with p
    a_sec = [x for x in F.S if x["name"] == "assembly"]
    if a_sec:
        a0 = a_sec[0]["t0"]
        ost = np.zeros(N)
        pat8 = [0, 0, 12, 0, 7, 0, 12, 7]
        for s, t, st, sec in steps:
            if sec["name"] != "assembly" or st % 2 != 0 or t < a0 + beat * 0.9 or t >= gs:
                continue
            p = float(np.clip((t - a0) / max(gs - a0, 1e-6), 0, 1))
            if p < 0.18:
                continue
            ch = CHORDS[chord_of[bar_of(t)]]
            semi = pat8[(st // 2) % 8]
            f = float(midi(ch["root"] + 12 + semi))
            n = int(0.24 * SR)
            tt = tvec(n)
            y = saw_blep(f) if False else saw_blep(np.full(n, f))
            y = y * np.exp(-tt / 0.09) * (0.5 + 0.5 * p) * (1.0 if st % 4 == 0 else 0.7)
            y = edges(y, 0.002, 0.02)
            i0 = int(round(t * SR))
            m_ = min(n, N - i0)
            ost[i0:i0 + m_] += y[:m_]
        pfc = np.interp(T, [a0, gs], [230.0, 2400.0])
        ost = tvfilter(ost, pfc, "lp", order=2, q=0.8)
        F.addtrack(M, ost * (0.55 + 0.45 * duck), gain=0.55, room=0.06)

    # 6. ticks (watch movement)
    trng = np.random.default_rng(23)
    tick_t = [tpl_tick(0, 1.0, trng), tpl_tick(1, 1.0, trng), tpl_tick(0, 0.8, trng), tpl_tick(1, 0.8, trng)]
    hat_c = tpl_hat(1.0, False, np.random.default_rng(5))
    hat_o = tpl_hat(1.0, True, np.random.default_rng(6))
    cnt = 0
    for s, t, st, sec in steps:
        nm = F.prof(sec["name"])
        if t >= t_groove_end + 0.0 and nm == "finale":
            continue
        if gs <= t < ign or nm in ("intro", "ignition"):
            continue
        vl = lv["tick"][min(int(t * SR), N - 1)]
        play = None
        if nm == "assembly":
            p = float(np.clip((t - a0) / max(gs - a0, 1e-6), 0, 1)) if a_sec else 0.5
            if t < a0 + 0.5 * beat:
                continue
            if p < 0.55:
                if st % 2 == 0:
                    play = (cnt % 2, 1.0 if st % 4 == 0 else 0.7)
            else:
                play = (cnt % 2, 1.0 if st % 4 == 0 else 0.6)
        elif nm == "hero_front":
            if st % 4 == 2:
                play = (cnt % 2 + 2, 0.7)
            elif st % 2 == 1:
                play = (cnt % 2 + 2, 0.4)
        elif nm in ("profile", "rear", "finale"):
            if st % 2 == 0 and st % 4 != 0:
                play = (cnt % 2, 0.9)
            elif st % 2 == 1:
                play = (cnt % 2 + 2, 0.5)
        elif nm == "doors":
            if st % 4 == 2:
                play = (cnt % 2, 0.6)
        elif nm == "interior":
            if st % 2 == 0:
                play = (cnt % 2, 1.0 if st % 8 == 0 else 0.8)
            elif st % 4 == 3:
                play = (cnt % 2 + 2, 0.4)
        if play is not None:
            kind, v = play
            pan = -0.45 if cnt % 2 == 0 else 0.45
            F.put(M, t, tick_t[kind], pan, gain=v * vl * 1.5, room=0.25, hall=0.08)
            cnt += 1

    # open hats / snare / clap in groove sections
    prng = np.random.default_rng(31)
    for s, t, st, sec in steps:
        nm = F.prof(sec["name"])
        if nm not in ("hero_front", "profile", "rear", "finale") or t >= t_groove_end:
            continue
        if nm == "hero_front":
            if st == 12:
                F.put(M, t, tpl_snare(0.55, prng), 0.05, gain=0.6, room=0.35, hall=0.25)
        else:
            if st in (4, 12):
                F.put(M, t, tpl_snare(1.0 if nm != "profile" else 0.85, prng), 0.0, gain=0.8, room=0.3, hall=0.3)
            if st == 6 or (nm in ("rear", "finale") and st == 14):
                F.put(M, t, hat_o, 0.35, gain=1.3, room=0.15)
        if nm in ("profile", "rear", "finale") and st % 2 == 0 and st not in (4, 12):
            F.put(M, t, hat_c, -0.3 if (st // 2) % 2 else 0.3, gain=0.9 + 0.3 * (st % 4 == 2))

    # 7. kicks
    log("kick / bass / pad")
    kt = tpl_kick(1.0)
    for t, v in kick_hits:
        F.put(M, t, kt, 0.0, gain=0.58 * v, room=0.05)

    # 8. sub bass following the progression
    bass = np.zeros(N)
    bpat = {
        "hero_front": [(0, 5), (6, 2), (10, 4)],
        "profile": [(0, 3), (4, 2), (6, 2), (10, 2), (12, 4)],
        "rear": [(0, 3), (4, 2), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)],
        "finale": [(0, 3), (4, 2), (6, 2), (10, 2), (12, 4)],
        "doors": [(0, 12)],
        "interior": [(0, 16)],
    }
    for k in range(kmin, kmax + 1):
        tb = t_down + k * bar
        if tb < 0 or tb >= dur:
            continue
        nm = F.prof(bar_sec[k])
        if nm not in bpat:
            continue
        ch = CHORDS[chord_of[k]]
        for st0, ln in bpat[nm]:
            t0_ = tb + st0 * s16
            if t0_ >= t_groove_end or t0_ < F.sec_at(min(max(t0_, 0), dur - 1e-6), True)["t0"] - 1e-6:
                continue
            f = float(midi(ch["bass"]))
            n = int((ln * s16 + 0.05) * SR)
            tt = tvec(n)
            y = np.sin(TWO_PI * f * tt) + 0.35 * np.sin(TWO_PI * 2 * f * tt + 0.7) + 0.1 * np.sin(TWO_PI * 3 * f * tt)
            y = np.tanh(1.5 * y) * 0.7
            env = smoothstep(tt / 0.012) * (1 - smoothstep((tt - ln * s16) / 0.05)) * np.exp(-tt / (ln * s16 * 1.8 + 0.1))
            i0 = int(round(t0_ * SR))
            m_ = min(n, N - i0)
            bass[i0:i0 + m_] += (y * env)[:m_]
    bass *= lv["bass"] * (0.35 + 0.65 * duck)
    F.addtrack(M, bass, gain=0.5)

    # 9. pad (analogue style supersaw chords, filtered, ducked)
    pad = np.zeros((2, N))
    detune = [-12.0, -4.0, 5.0, 13.0]
    pans = [-0.8, -0.3, 0.3, 0.8]
    kmin_pad = None
    pad_start = a_sec[0]["t0"] if a_sec else 0.0
    segs = []
    for k in range(kmin, kmax + 1):
        tb = t_down + k * bar
        te = tb + bar
        if te < pad_start or tb > dur:
            continue
        nm = F.prof(bar_sec[k])
        if nm == "intro":
            continue
        ts, tend = max(tb, pad_start), te
        if nm == "finale" and k > k_fin:
            continue
        if k == k_fin:
            tend = min(tend, F.t_final)
        if k == k_fin + 1 or tb >= F.t_final:
            continue
        segs.append((ts, tend, chord_of[k], False))
    segs.append((F.t_final, dur, "Dm", True))
    for ts, tend, cn, final in segs:
        i0 = int(round((ts - (0.05 if not final else 0.0)) * SR))
        i1 = min(int(round((tend + (0.6 if not final else 0.0)) * SR)), N)
        n = i1 - i0
        if n <= 100:
            continue
        tt = tvec(n)
        att = 0.5 if not final else 0.12
        env = smoothstep(tt / att) * (1 - smoothstep((tt - (n / SR - 0.7)) / 0.7)) if not final else smoothstep(tt / att)
        ch = CHORDS[cn]
        notes = list(ch["pad"])
        if final:
            notes = notes + [76 + 0, 81]
        for mi, m_ in enumerate(notes):
            f = float(midi(m_))
            for v in range(4):
                fr = f * 2 ** (detune[v] / 1200.0) * (1 + 0.0007 * np.sin(TWO_PI * (0.2 + 0.07 * v) * tt + mi))
                y = saw_blep(fr, phase0=(0.13 * mi + 0.31 * v) % 1.0) * env
                a_ = 0.16 / (1 + 0.04 * max(m_ - 60, 0))
                th = (pans[(v + mi) % 4] + 1) * np.pi / 4
                pad[0, i0:i1] += y * a_ * np.cos(th)
                pad[1, i0:i1] += y * a_ * np.sin(th)
    pad_l = tvfilter(pad[0], padfc, "lp", order=2, q=0.5, hop=1024)
    pad_r = tvfilter(pad[1], padfc * 1.03, "lp", order=2, q=0.5, hop=1024)
    pad = np.stack([pad_l, pad_r]) * lv["pad"] * (0.35 + 0.65 * duck)
    F.addtrack(M, pad, gain=1.15, hall=0.5)

    # 10. lead motif (bell / pluck) with ping-pong dotted-eighth delay
    log("lead / arp")
    lead = np.zeros((2, N))
    arp = np.zeros((2, N))
    for k in range(kmin, kmax + 1):
        tb = t_down + k * bar
        if tb < -bar or tb >= dur:
            continue
        nm = F.prof(bar_sec[k])
        cn = chord_of[k]
        ch = CHORDS[cn]
        sec = F.sec_at(min(max(tb + 0.5 * bar, 0), dur - 1e-6))
        tend_ok = F.t_final - 0.02
        if nm in ("hero_front", "profile", "rear", "doors", "finale"):
            for st0, m_, ln in MOTIF[cn]:
                t0_ = tb + st0 * s16
                if t0_ < F.snap(sec["t0"]) - 1e-6 or t0_ >= tend_ok:
                    continue
                if nm == "hero_front" and (k - first_of[bar_sec[k]]) % 4 in (1,) and st0 >= 6:
                    pass
                v = lv["lead"][min(int(t0_ * SR), N - 1)]
                if v <= 0.01:
                    continue
                sus = min(ln * s16 * 1.5 + 0.4, 2.0)
                b = tpl_bell(float(midi(m_)), sus, v, 1.0)
                F.put(M, t0_, b, 0.12, gain=1.0, hall=0.4)
                lead_note = b
                i0 = int(round(t0_ * SR))
                mm = min(len(b), N - i0)
                lead[0, i0:i0 + mm] += b[:mm] * 0.7
                lead[1, i0:i0 + mm] += b[:mm] * 0.7
                if nm in ("rear", "finale") or (nm == "profile" and st0 == 8):
                    b2 = tpl_bell(float(midi(m_ + 12)), min(sus, 1.2), v * 0.45, 1.2)
                    F.put(M, t0_ + 0.004, b2, -0.25, gain=0.8, hall=0.45)
        # arpeggio of glassy plucks
        if nm in ("profile", "rear", "doors", "interior", "finale"):
            tones = [m_ + 12 for m_ in ch["pad"]]
            stp = 2 if nm in ("rear", "doors", "finale", "profile") else 3
            pat = [0, 2, 3, 4, 3, 2, 4, 3] if nm != "interior" else [0, 3, 2, 4, 3, 1]
            if nm == "interior":
                stp = 3
            for j, st0 in enumerate(range(0, 16, stp)):
                t0_ = tb + st0 * s16
                if t0_ < F.snap(sec["t0"]) - 1e-6 or t0_ >= F.t_final - 0.02 or (gs <= t0_ < ign):
                    continue
                if nm in ("profile", "finale") and j % 2 == 1:
                    continue
                v = lv["arp"][min(int(t0_ * SR), N - 1)]
                if v <= 0.01:
                    continue
                m_ = tones[pat[j % len(pat)]] + (12 if nm in ("interior", "doors") and j % 3 == 2 else 0)
                b = tpl_bell(float(midi(m_)), 0.9 if nm != "interior" else 1.4, v * (0.8 if j % 2 else 1.0), kind="glass")
                F.put(M, t0_, b, ((j * 0.37) % 1.2) - 0.6, gain=0.85, hall=0.5)
                i0 = int(round(t0_ * SR))
                mm = min(len(b), N - i0)
                arp[0, i0:i0 + mm] += b[:mm] * 0.25
                arp[1, i0:i0 + mm] += b[:mm] * 0.25

    # delay on lead and arp: tempo-synced dotted eighth, ping-pong
    d = int(round(0.75 * beat * SR))
    src = lead[0] + arp[0] * 0.6
    lp1 = sfilter(src, "lp", 4500, 2)
    lp2 = sfilter(src, "lp", 2200, 2)
    dl = np.zeros((2, N))
    fb = 0.5
    for k in range(1, 7):
        sh_ = d * k
        if sh_ >= N:
            break
        sig = (lp1 if k <= 2 else lp2)
        g = fb ** k
        side = 0.6 if k % 2 else -0.6
        th = (side + 1) * np.pi / 4
        dl[0, sh_:] += sig[: N - sh_] * g * np.cos(th)
        dl[1, sh_:] += sig[: N - sh_] * g * np.sin(th)
    F.addtrack(M, dl, gain=0.8, hall=0.5)

    # 11. event sounds
    log("events")
    erng = np.random.default_rng(2024)
    lands = F.ev("land")
    whs = F.ev("whoosh")
    used = set()
    pairs = []
    for w in whs:
        cand = [i for i, l in enumerate(lands) if i not in used and l["t"] > w["t"] + 0.1]
        same = [i for i in cand if lands[i].get("label") == w.get("label")]
        pick = same[0] if same else (cand[0] if cand else None)
        if pick is not None:
            used.add(pick)
            pairs.append((w["t"], lands[pick]["t"], lands[pick].get("weight", 0.6)))
        else:
            pairs.append((w["t"], w["t"] + 0.7, 0.5))
    for tw, tl_, wt in pairs:
        d_ = min(max(tl_ - tw, 0.25), 1.6)
        y = tpl_whoosh(d_, erng, 1.0)
        side = -1.0 if erng.random() < 0.5 else 1.0
        p = np.clip(tvec(len(y)) / d_, 0, 1)
        pan = side * 0.85 * (1 - smoothstep(p)) + side * 0.1
        th = (pan + 1) * np.pi / 4
        st = np.stack([y * np.cos(th), y * np.sin(th)])
        F.put(M, tl_ - d_, st, gain=0.16 * (0.6 + 0.6 * wt) * 1.0, hall=0.35, room=0.2)
    thud_t = F.t_final
    for i, e in enumerate(lands):
        wt = float(e.get("weight", 0.6))
        if abs(e["t"] - thud_t) < 1e-6 and e["t"] > 0.75 * dur:
            continue
        c = tpl_clunk(wt, np.random.default_rng(500 + i))
        pan = float(np.clip(np.random.default_rng(900 + i).uniform(-0.55, 0.55), -0.6, 0.6))
        F.put(M, e["t"], c, pan, gain=0.55 * (0.6 + 0.5 * wt), room=0.5, hall=0.15)
    # final thud (deep, satisfying) goes into the ungated bus
    F.put(X, thud_t, tpl_clunk(0.9, np.random.default_rng(777)), 0.0, gain=0.5, room=0.45, hall=0.3)
    F.put(X, thud_t, tpl_thud(1.0), 0.0, gain=0.75, hall=0.25)

    # servo whirr
    srv = np.random.default_rng(55)
    for e in F.ev("wing_up"):
        y = tpl_servo(0.95, 190, 560, srv, 0.75)
        F.put(M, e["t"], y, 0.35, gain=0.55, hall=0.3, room=0.1)
        F.put(M, e["t"] + 0.95, tpl_clunk(0.25, np.random.default_rng(31)), 0.35, gain=0.14, room=0.4)
    for e in F.ev("wing_down"):
        y = tpl_servo(0.85, 520, 170, srv, 0.65)
        F.put(M, e["t"], y, 0.35, gain=0.55, hall=0.3, room=0.1)
        F.put(M, e["t"] + 0.85, tpl_clunk(0.25, np.random.default_rng(32)), 0.35, gain=0.14, room=0.4)
    for e in F.ev("door_open"):
        y = tpl_servo(1.3, 140, 640, srv, 1.0)
        F.put(M, e["t"], y, 0.0, gain=0.7, hall=0.35, room=0.1)
        # soft rising air + landing hiss
        n = int(1.5 * SR)
        tt = tvec(n)
        nz = tvfilter(srv.standard_normal(n), 500 * (6.0) ** (tt / 1.3), "bp", q=0.9, hop=512)
        env = np.sin(0.5 * np.pi * np.clip(tt / 1.3, 0, 1)) ** 2 * (1 - smoothstep((tt - 1.3) / 0.2))
        F.put(M, e["t"], edges(nz * env, 0.05, 0.05), 0.0, gain=0.07, hall=0.5)
        F.put(M, e["t"] + 1.3, tpl_clunk(0.35, np.random.default_rng(41)), 0.0, gain=0.22, room=0.5, hall=0.3)
    for e in F.ev("door_close"):
        ends = [l["t"] for l in lands if l["t"] > e["t"] and l["t"] - e["t"] < 2.5]
        d_ = (ends[0] - e["t"]) if ends else 1.3
        y = tpl_servo(d_, 600, 150, srv, 1.0, tail=0.05)
        F.put(M, e["t"], y, 0.0, gain=0.7, hall=0.35, room=0.1)
    for e in F.ev("screen"):
        # glass "tap" transient followed by a small crystalline three-note chime (Dm add9 colour)
        F.put(M, e["t"], tpl_tick(1, 1.3, np.random.default_rng(70)), 0.2, gain=0.8, room=0.3, hall=0.2)
        for j, m_ in enumerate((88, 93, 100)):
            F.put(M, e["t"] + 0.07 * j, tpl_chime(float(midi(m_)), 1.8, 1.0 - 0.12 * j), -0.35 + 0.35 * j, gain=0.5, hall=0.7)

    # 12. riser into the ignition
    log("riser, ignition")
    if a_sec:
        rl = min(4.5, 0.7 * (gs - a0))
        r0 = gs - rl
        i0 = int(r0 * SR)
        i1 = int(gs * SR)
        n = i1 - i0
        tt = tvec(n)
        p = tt / (n / SR)
        nz = srv.standard_normal((2, n))
        fcn = 300.0 * (9500.0 / 300.0) ** (p ** 1.1)
        nz = np.stack([tvfilter(nz[0], fcn, "bp", q=0.9, hop=512), tvfilter(nz[1], fcn, "bp", q=0.9, hop=512)])
        env = p ** 2.3 * smoothstep(tt / 0.4)
        r_n = nz * env * 0.55
        # tonal saw glide up to D5
        fr = float(midi(50)) * 2 ** (2.0 * p ** 1.3)
        tone = np.zeros((2, n))
        for v, dt_ in enumerate((-9, 0, 9)):
            for ch in range(2):
                y = saw_blep(fr * 2 ** ((dt_ + 3 * ch) / 1200.0), phase0=0.2 * v)
                tone[ch] += y * 0.2
        tfc = 400.0 * (6000.0 / 400.0) ** p
        tone = np.stack([tvfilter(tone[0], tfc, "lp", q=0.6, hop=512), tvfilter(tone[1], tfc, "lp", q=0.6, hop=512)]) * (p ** 1.8) * 0.9
        full = np.zeros((2, N))
        full[:, i0:i1] = r_n + tone
        F.addtrack(M, full, gain=0.5, hall=0.3)

    # 13. ignition hit: sub impact, wide chord stab, engine start
    ti = ign
    n = int(2.4 * SR)
    tt = tvec(n)
    f = 34.0 + 70.0 * np.exp(-tt / 0.07)
    sub = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-tt / 0.75)
    sub = np.tanh(1.3 * sub)
    boom = sfilter(np.random.default_rng(3).standard_normal(n), "lp", 190, 2) * np.exp(-tt / 0.55) * 1.3
    air = sfilter(np.random.default_rng(4).standard_normal((2, n)), "hp", 3500, 2) * np.exp(-tt / 0.9) * 0.1
    hit = edges(sub * 0.95 + boom * 0.6, 0.001, 0.2)
    F.put(X, ti, hit, 0.0, gain=1.5, room=0.1, hall=0.1)
    F.put(X, ti, edges(air, 0.001, 0.3), 0.0, gain=2.0, hall=0.5)
    # chord stab: Dm add9, wide, bright closing filter
    cn = int(2.8 * SR)
    ct = tvec(cn)
    stab = np.zeros((2, cn))
    stab_notes = [50, 57, 62, 65, 69, 74, 76, 81]
    for mi, m_ in enumerate(stab_notes):
        for v in range(4):
            fr = float(midi(m_)) * 2 ** ((detune[v] * 1.2) / 1200.0)
            y = saw_blep(np.full(cn, fr), phase0=(0.17 * mi + 0.29 * v) % 1)
            th = (pans[(v + mi) % 4] * 0.95 + 1) * np.pi / 4
            a_ = 0.12 / (1 + 0.025 * max(m_ - 60, 0))
            stab[0] += y * a_ * np.cos(th)
            stab[1] += y * a_ * np.sin(th)
    senv = smoothstep(ct / 0.006) * np.exp(-ct / 1.0)
    sfc = 9500.0 * np.exp(-ct / 0.9) + 1200.0
    stab = np.stack([tvfilter(stab[0], sfc, "lp", q=0.4, hop=512), tvfilter(stab[1], sfc * 1.02, "lp", q=0.4, hop=512)]) * senv
    F.put(X, ti, edges(stab, 0.002, 0.3), gain=2.8, hall=0.6)

    # engine start
    ed = 3.0
    en = int(ed * SR)
    et = tvec(en)
    erng2 = np.random.default_rng(88)
    kt_ = [0.0, 0.03, 0.09, 0.22, 0.36, 0.55, 0.8, 1.2, 2.6, 3.0]
    kf = [38.0, 70.0, 175.0, 340.0, 262.0, 172.0, 150.0, 146.8, 146.8, 140.0]
    fe = np.interp(et, kt_, kf)
    fe = boxsmooth(fe, 0.02 * SR)
    eng = np.zeros((2, en))
    for ch in range(2):
        rough = sfilter(erng2.standard_normal(en), "lp", 45, 2)
        rough /= np.std(rough) + 1e-9
        jit = sfilter(erng2.standard_normal(en), "lp", 30, 2)
        jit /= np.std(jit) + 1e-9
        ff = fe * (1 + 0.0025 * jit * np.interp(et, [0, 0.8, 1.2], [3.0, 1.5, 0.6]))
        ph = TWO_PI * np.cumsum(ff) / SR
        y = np.zeros(en)
        fcut = 650.0 + 5.0 * ff
        for k in range(1, 31):
            if k * 340.0 > 11000:
                break
            a = k ** -1.15 / np.sqrt(1.0 + (k * ff / fcut) ** 4)
            a = a * (1.0 + 0.12 * rough * ((k * 1.3) % 1.0 + 0.3))
            y += a * np.sin(k * ph + 1.7 * k + 0.9 * ch * k % 3)
        # engine orders (rotational, 1/8 of firing): the "lump" of a V16 at idle
        for m_, a in ((1, 0.2), (2, 0.14), (3, 0.1), (4, 0.22), (5, 0.07), (6, 0.1), (7, 0.05)):
            y += a * np.sin(ph * m_ / 8.0 + 0.7 * m_ + ch)
        # exhaust: band noise gated by each firing pulse
        pulse = 0.55 + 0.45 * np.cos(ph) ** 2
        ex = sfilter(erng2.standard_normal(en), "bp", 480.0, 1, q=0.45) * pulse
        y = y * 0.35 + ex * 0.3 * (1.0 + 0.9 * np.exp(-et / 0.45))
        eng[ch] = y
    eenv = np.interp(et, [0, 0.008, 0.07, 0.2, 0.45, 0.8, 1.9, 2.5, 3.0], [0, 0.55, 0.9, 1.0, 0.62, 0.5, 0.42, 0.18, 0])
    eng = np.tanh(1.6 * eng * eenv) / 1.6
    eng = sfilter(eng, "lp", 4800, 2)
    eng = sfilter(eng, "hp", 45, 2)
    # sputter at the very start: three ignition pops
    F.put(X, ti, eng, gain=1.3, hall=0.2, room=0.1)
    log("buses done, reverbs")

    # ---------------------------------------------------------------- reverbs
    def make_ir(rt60, seed, hf0, hf1, pre):
        L = int(rt60 * 1.15 * SR)
        r = np.random.default_rng(seed)
        t = tvec(L)
        chans = []
        for c in range(2):
            x = r.standard_normal(L) * 10 ** (-3 * t / rt60) * smoothstep(t / 0.012)
            x = tvfilter(x, hf0 * (hf1 / hf0) ** (t / (L / SR)), "lp", order=2, hop=1024)
            x = sfilter(x, "hp", 140, 2)
            chans.append(np.concatenate([np.zeros(int(pre * SR)), x]))
        ir = np.stack(chans)
        ir /= np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True)) + 1e-9
        return ir

    ir_hall = make_ir(3.6, 101, 8500.0, 1400.0, 0.022)
    ir_room = make_ir(0.55, 102, 9000.0, 2500.0, 0.004)

    def reverb(bus_in, ir):
        m = 0.5 * (bus_in[0] + bus_in[1])
        m = sfilter(m, "hp", 160, 2)
        return np.stack([fftconv(m, ir[0]), fftconv(m, ir[1])])

    for B in (M, X):
        if B is M:
            for k in B:
                B[k] = B[k] * gate[None, :]
    wet_hall = reverb(M["hall"] + X["hall"], ir_hall)
    wet_room = reverb(M["room"] + X["room"], ir_room)
    mix = M["dry"] + X["dry"] + wet_hall * 0.9 + wet_room * 0.8
    log("master")

    # ---------------------------------------------------------------- master
    mix = sfilter(mix, "hp", 25.0, 4)  # remove DC / sub rumble
    mix = mix + 0.4 * sfilter(mix, "hp", 6500.0, 2)  # gentle air shelf (+3 dB above ~7 kHz)
    # mono bass: side channel high-passed at 120 Hz
    mid = 0.5 * (mix[0] + mix[1])
    side = 0.5 * (mix[0] - mix[1])
    side = sfilter(side, "hp", 120.0, 2)
    mix = np.stack([mid + side, mid - side])
    # fade in / fade out
    fade = np.ones(N)
    fi = int(0.05 * SR)
    fade[:fi] = smoothstep(np.arange(fi) / fi)
    tf = F.t_fade
    ie = int((dur - 0.01) * SR)
    i0 = int(tf * SR)
    if ie > i0:
        p = np.arange(ie - i0) / (ie - i0)
        fade[i0:ie] = np.cos(0.5 * np.pi * p) ** 2
    fade[ie:] = 0.0
    mix = mix * fade[None, :]

    target = -15.0
    g = 10 ** ((target - integrated_lufs(mix)) / 20.0)
    ceil_ = [10 ** (-2.0 / 20.0)]

    def process(gv):
        y = mix * gv
        thr = 0.62  # gentle soft clip above 0.62 to tame stray peaks
        a = np.abs(y)
        y = np.where(a > thr, np.sign(y) * (thr + (1 - thr) * np.tanh((a - thr) / (1 - thr))), y)
        return limiter(y, ceil_[0])

    for it in range(8):
        y = process(g)
        L_ = integrated_lufs(y)
        tp_ = true_peak(y)
        tp_lim = 10 ** (-1.1 / 20.0)
        if tp_ > tp_lim:  # inter-sample peaks: lower the limiter ceiling
            ceil_[0] *= tp_lim / tp_
            continue
        if abs(L_ - target) < 0.08:
            break
        g *= 10 ** ((target - L_) / 20.0)
    pre = np.max(np.abs(mix * g), axis=0)
    post = np.max(np.abs(y), axis=0)
    gr = 20 * np.log10(np.maximum(post, 1e-9) / np.maximum(pre, 1e-9))
    log("limiter/soft clip: max reduction %.1f dB, >1 dB on %.2f %% of samples, >3 dB on %.3f %%" % (-gr.min(), 100 * np.mean(gr < -1), 100 * np.mean(gr < -3)))
    tp = true_peak(y)
    lim = 10 ** (-1.2 / 20.0)
    if tp > lim:
        y = y * (lim / tp)
    y[:, ie:] = 0.0
    y -= 0  # no DC offset removal needed (high-passed)
    y = np.clip(y, -0.999, 0.999)
    log("final integrated %.2f LUFS, true peak %.2f dBTP, sample peak %.2f dBFS" % (integrated_lufs(y), 20 * np.log10(true_peak(y)), 20 * np.log10(np.max(np.abs(y)))))

    write_wav(out_path, y)
    log("wrote", out_path)
    return F, y


def write_wav(path, y):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    q = np.round(y.T * 8388607.0).astype(np.int32)
    b = q.astype("<i4").tobytes()
    raw = np.frombuffer(b, dtype=np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(raw)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=os.path.join(root, "anim", "timeline.json"))
    ap.add_argument("--out", default=os.path.join(root, "out", "audio", "soundtrack.wav"))
    a = ap.parse_args()
    render(a.timeline, a.out)
