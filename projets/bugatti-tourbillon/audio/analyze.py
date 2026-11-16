#!/usr/bin/env python3
"""Analytic verification of the soundtrack (no listening possible)."""
import argparse, json, os, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_music as mm

SR = 48000


def read_wav(p):
    with wave.open(p) as w:
        n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw == 3:
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v) / 8388608.0
    else:
        v = np.frombuffer(raw, dtype="<i2") / 32768.0
    return v.reshape(-1, ch).T


def band_shares(x):
    X = np.abs(np.fft.rfft(x.mean(0) if x.ndim == 2 else x)) ** 2
    f = np.fft.rfftfreq(x.shape[-1], 1 / SR)
    edges = [0, 100, 1000, 5000, 24001]
    e = np.array([X[(f >= a) & (f < b)].sum() for a, b in zip(edges[:-1], edges[1:])])
    return e / max(e.sum(), 1e-20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default="out/audio/soundtrack.wav")
    ap.add_argument("--timeline", default="anim/timeline.json")
    a = ap.parse_args()
    y = read_wav(a.wav)
    tl = json.load(open(a.timeline))
    dur = tl["duration"]
    print("file: %.3f s, %d ch, peak %.2f dBFS, true peak %.2f dBTP, DC L %.2e R %.2e, last 10 ms max %.2e"
          % (y.shape[1] / SR, y.shape[0], 20 * np.log10(np.abs(y).max()), 20 * np.log10(mm.true_peak(y)), y[0].mean(), y[1].mean(), np.abs(y[:, -480:]).max()))
    print("integrated %.2f LUFS (own meter)" % mm.integrated_lufs(y))
    # mono bass
    lo = mm.sfilter(y, "lp", 120.0, 4)
    print("bass (<120 Hz) L/R correlation %.4f, side/mid energy ratio %.1f dB" % (np.corrcoef(lo[0], lo[1])[0, 1], 10 * np.log10((np.sum((lo[0] - lo[1]) ** 2) + 1e-20) / (np.sum((lo[0] + lo[1]) ** 2) + 1e-20))))
    lb, tb = mm.lufs_blocks(y)
    print("\nper section (momentary 400 ms loudness LUFS: mean / max; band shares <100 | 100-1k | 1-5k | >5k in %)")
    for s in tl["sections"]:
        i0, i1 = int(s["t0"] * SR), min(int(s["t1"] * SR), y.shape[1])
        m = (tb >= s["t0"]) & (tb + 0.4 <= s["t1"] + 0.2)
        bl = lb[m] if m.any() else lb[:1]
        rms = 20 * np.log10(np.sqrt(np.mean(y[:, i0:i1] ** 2)) + 1e-12)
        bs = band_shares(y[:, i0:i1]) * 100
        print("  %-10s %5.1f-%5.1f  rms %6.1f dB  mom LUFS mean %6.1f max %6.1f   %4.1f | %4.1f | %4.1f | %4.1f" % (s["name"], s["t0"], s["t1"], rms, np.mean(bl), np.max(bl), *bs))
    k = np.argmax(lb)
    print("loudest 400 ms block starts at %.2f s (%.1f LUFS)" % (tb[k], lb[k]))
    # 100 ms window peak levels around the ignition
    ign = [e["t"] for e in tl["events"] if e["type"] == "ignition"]
    # onset check
    print("\nevent onset check: transient = 1 ms envelope of the 1.5-14 kHz band (clicks, ticks, chords) and 40-250 Hz band (thumps);")
    print("  'dt' = time of the strongest positive flux within +-30 ms of the event, 'x' = that flux relative to the median flux of the +-0.5 s neighbourhood")
    m = y.mean(0)
    hi = mm.sfilter(mm.sfilter(m, "hp", 1500.0, 2), "lp", 14000.0, 2)
    lo = mm.sfilter(mm.sfilter(m, "hp", 40.0, 2), "lp", 250.0, 2)
    mid = mm.sfilter(mm.sfilter(m, "hp", 300.0, 2), "lp", 6000.0, 2)
    w = int(0.002 * SR)
    def envdb(x):
        e = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, mode="same"))
        return 20 * np.log10(e + 1e-9)
    E_hi, E_lo, E_mid = envdb(hi), envdb(lo), envdb(mid)
    ok = 0
    tot = 0
    for e in tl["events"]:
        t = e["t"]
        i = int(t * SR)
        typ = e["type"]
        if i >= len(m) - 3000:
            print("  %-10s %6.2f  (inside final fade, skipped)" % (typ, t)); continue
        best = None
        for nm_, E in ((("hi", E_hi), ("lo", E_lo)) if typ in ("land", "ignition") else (("hi", E_hi), ("mid", E_mid))):
            lo_, hi_ = max(i - int(0.03 * SR), 2), i + int(0.03 * SR)
            seg = E[lo_:hi_]
            dlt = np.array([seg[min(k + int(0.006 * SR), len(seg) - 1)] - seg[k] for k in range(len(seg))])
            j = int(np.argmax(dlt))
            bg = E[max(i - int(0.5 * SR), 0):i + int(0.5 * SR)]
            bgd = np.abs(bg[int(0.006 * SR):] - bg[:-int(0.006 * SR)])
            ratio = dlt[j] / (np.median(bgd) + 1e-3)
            if best is None or dlt[j] > best[1]:
                best = (nm_, dlt[j], (lo_ + j - i) / SR * 1000, ratio)
        slow = typ not in ("land", "ignition", "screen")
        tot += 1
        if slow:
            flag = "gradual by design (rise %+.1f dB)" % best[1]
            ok += 1
        elif best[1] > 6.0 and abs(best[2]) <= 30:
            flag = "ok"
            ok += 1
        else:
            flag = "WEAK"
        pk = np.abs(y[:, i:i + int(0.1 * SR)]).max()
        print("  %-10s %6.2f %-24s band %-3s rise %+5.1f dB/6ms at %+4.0f ms (x%4.1f of bg)  peak100ms %6.1f dBFS  %s" % (typ, t, e.get("label", "")[:24], best[0], best[1], best[2], best[3], 20 * np.log10(pk), flag))
    print("  -> %d / %d events with a clear transient (land / ignition / screen) or a gradual-by-design envelope" % (ok, tot))
    out = os.path.join(os.path.dirname(a.wav), "spectrogram.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.wav, "-lavfi", "showspectrumpic=s=1600x800:legend=1", out])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.wav, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr.split("Summary:")[-1]
    print("\nffmpeg ebur128 summary:" + tail)


if __name__ == "__main__":
    main()
