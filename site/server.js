// Serveur de l'outil de revision.
// Le navigateur ne parle jamais directement a l'API Claude : il appelle ce
// serveur, qui garde la cle API secrete et relaie les reponses.

import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import Anthropic from "@anthropic-ai/sdk";
import { betaZodOutputFormat } from "@anthropic-ai/sdk/helpers/beta/zod";
import { z } from "zod";

const here = path.dirname(fileURLToPath(import.meta.url));

const PORT = Number(process.env.PORT) || 3000;
const MODEL = process.env.CLAUDE_MODEL || "claude-opus-5-5";
const SITE_PASSWORD = process.env.SITE_PASSWORD || "";
const DAILY_LIMIT = Number(process.env.DAILY_LIMIT) || 100;

// Si le modele refuse une demande (filtre de securite), l'API la rejoue
// automatiquement sur un modele de secours au lieu de renvoyer une erreur.
const FALLBACK = {
  betas: ["server-side-fallback-2026-07-01"],
  fallbacks: "default",
};

// Lit ANTHROPIC_API_KEY dans l'environnement.
const client = new Anthropic();

const SUBJECTS = [
  "Français",
  "Mathématiques",
  "Histoire-Géographie",
  "Physique-Chimie",
  "SVT",
  "SES",
  "Anglais",
  "Espagnol",
  "Autre",
];
const LEVELS = ["Seconde", "Première", "Terminale"];

const BASE_PROMPT = `Tu es Alfred, l'assistant de révision d'un lycéen en filière française (programme de l'Éducation nationale).
Règles :
- Réponds en français, en tutoyant l'élève. Si la matière est une langue vivante, donne les exemples dans cette langue et les explications en français.
- Sois exact. Si tu n'es pas sûr d'un fait (date, citation, formule), dis-le plutôt que d'inventer. Ne fabrique jamais de citation d'auteur.
- Adapte le niveau à la classe indiquée.
- Aucun emoji. Pas de tirets longs.
- Mets en forme en Markdown simple : titres (## et ###), listes à puces, gras. Pas de tableaux, pas de LaTeX : écris les formules en texte clair (par exemple x^2, racine(x)).`;

const PROMPTS = {
  explain: `${BASE_PROMPT}

Mode : explication. L'élève pose des questions sur son cours. Explique clairement, avec un exemple concret quand c'est utile, et va droit au but. Une question simple mérite une réponse courte. Ne fais pas ses devoirs à sa place : pour un exercice ou une rédaction, guide-le par étapes et laisse-le produire le résultat.`,
  sheet: `${BASE_PROMPT}

Mode : fiche de révision. Produis une fiche synthétique que l'élève peut relire la veille d'un contrôle, avec cette structure :
## L'essentiel (3 à 5 phrases)
## Notions clés (définitions courtes)
## À retenir (dates, formules, auteurs, méthodes selon la matière)
## Erreurs fréquentes
## Pour vérifier que tu as compris (3 questions, sans les réponses)
Reste dense : une fiche, pas un cours.`,
  quiz: `${BASE_PROMPT}

Mode : quiz. Écris des questions à choix multiples sur le sujet donné. Chaque question a exactement quatre propositions, une seule correcte, et des mauvaises réponses plausibles (les erreurs que ferait un élève). Varie la position de la bonne réponse. L'explication dit en une ou deux phrases pourquoi la bonne réponse est juste. Texte brut uniquement dans les champs, sans Markdown.`,
};

const QuizSchema = z.object({
  questions: z.array(
    z.object({
      question: z.string(),
      choices: z.array(z.string()),
      answer_index: z.number().int(),
      explanation: z.string(),
    }),
  ),
});

// --- Protections -----------------------------------------------------------

// Limite simple par adresse IP, en memoire : evite qu'un inconnu vide le
// credit API si le site est public. Remise a zero chaque jour.
const usage = new Map();
let usageDay = new Date().toDateString();

function rateLimit(req, res, next) {
  const today = new Date().toDateString();
  if (today !== usageDay) {
    usage.clear();
    usageDay = today;
  }
  const count = (usage.get(req.ip) || 0) + 1;
  usage.set(req.ip, count);
  if (count > DAILY_LIMIT) {
    return res
      .status(429)
      .json({ error: "Limite quotidienne atteinte. Reviens demain." });
  }
  next();
}

function checkPassword(req, res, next) {
  if (SITE_PASSWORD && req.get("x-site-password") !== SITE_PASSWORD) {
    return res.status(401).json({ error: "Mot de passe incorrect." });
  }
  next();
}

function cleanText(value, max) {
  if (typeof value !== "string") return "";
  return value.trim().slice(0, max);
}

function readContext(body) {
  const subject = SUBJECTS.includes(body.subject) ? body.subject : "Autre";
  const level = LEVELS.includes(body.level) ? body.level : "Seconde";
  return { subject, level, header: `Matière : ${subject}. Classe : ${level}.` };
}

function errorMessage(error) {
  if (error instanceof Anthropic.AuthenticationError) {
    return "Clé API absente ou invalide. Vérifie ANTHROPIC_API_KEY côté serveur.";
  }
  if (error instanceof Anthropic.RateLimitError) {
    return "Trop de demandes d'un coup. Réessaie dans une minute.";
  }
  if (error instanceof Anthropic.APIConnectionError) {
    return "Impossible de joindre l'API Claude. Réessaie.";
  }
  if (error instanceof Anthropic.APIError) {
    if (error.status >= 500) return "L'API Claude est surchargée. Réessaie.";
    return `Erreur de l'API (${error.status}).`;
  }
  // Le SDK leve une erreur simple quand aucune cle n'est configuree.
  if (!process.env.ANTHROPIC_API_KEY && !process.env.ANTHROPIC_AUTH_TOKEN) {
    return "Aucune clé API configurée. Ajoute ANTHROPIC_API_KEY dans le fichier .env.";
  }
  return "Erreur inattendue côté serveur.";
}

// Relaie la reponse de Claude au navigateur au fil de l'eau (texte brut).
async function streamAnswer(res, params) {
  let started = false;
  try {
    const stream = client.beta.messages.stream({
      model: MODEL,
      max_tokens: 16000,
      output_config: { effort: "medium" },
      ...FALLBACK,
      ...params,
    });
    res.on("close", () => stream.abort());

    stream.on("text", (delta) => {
      if (!started) {
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("X-Accel-Buffering", "no");
        started = true;
      }
      res.write(delta);
    });

    const message = await stream.finalMessage();
    if (message.stop_reason === "refusal") {
      if (!started) {
        return res
          .status(422)
          .json({ error: "Alfred ne peut pas répondre à cette demande." });
      }
      res.write("\n\n[Réponse interrompue : demande refusée.]");
    } else if (message.stop_reason === "max_tokens") {
      res.write("\n\n[Réponse coupée : trop longue.]");
    }
    res.end();
  } catch (error) {
    if (error instanceof Anthropic.APIUserAbortError) return;
    console.error(error);
    if (started) {
      res.write(`\n\n[${errorMessage(error)}]`);
      res.end();
    } else {
      res.status(500).json({ error: errorMessage(error) });
    }
  }
}

// --- Routes ----------------------------------------------------------------

const app = express();
app.set("trust proxy", 1);
app.use(express.json({ limit: "200kb" }));
app.use(express.static(path.join(here, "public")));

app.get("/api/config", (req, res) => {
  res.json({
    subjects: SUBJECTS,
    levels: LEVELS,
    passwordRequired: Boolean(SITE_PASSWORD),
  });
});

app.use("/api", checkPassword, rateLimit);

// Explication : conversation a plusieurs tours.
app.post("/api/explain", async (req, res) => {
  const { header } = readContext(req.body);
  const raw = Array.isArray(req.body.messages) ? req.body.messages : [];
  const messages = raw
    .slice(-20)
    .map((m) => ({
      role: m?.role === "assistant" ? "assistant" : "user",
      content: cleanText(m?.content, 6000),
    }))
    .filter((m) => m.content);
  while (messages.length && messages[0].role !== "user") messages.shift();
  if (!messages.length || messages.at(-1).role !== "user") {
    return res.status(400).json({ error: "Pose une question." });
  }
  await streamAnswer(res, {
    system: `${PROMPTS.explain}\n\n${header}`,
    messages,
  });
});

// Fiche de revision.
app.post("/api/sheet", async (req, res) => {
  const { header } = readContext(req.body);
  const topic = cleanText(req.body.topic, 300);
  const notes = cleanText(req.body.notes, 12000);
  if (!topic) return res.status(400).json({ error: "Indique un sujet." });
  let content = `${header}\nSujet de la fiche : ${topic}`;
  if (notes) {
    content += `\n\nVoici mes notes de cours. Appuie-toi dessus en priorité, corrige les erreurs éventuelles en le signalant :\n<notes>\n${notes}\n</notes>`;
  }
  await streamAnswer(res, {
    system: PROMPTS.sheet,
    messages: [{ role: "user", content }],
  });
});

// Quiz : reponse JSON structuree, validee par le schema.
app.post("/api/quiz", async (req, res) => {
  const { header } = readContext(req.body);
  const topic = cleanText(req.body.topic, 300);
  const count = Math.min(Math.max(Number(req.body.count) || 5, 3), 10);
  if (!topic) return res.status(400).json({ error: "Indique un sujet." });
  try {
    const message = await client.beta.messages.parse({
      model: MODEL,
      max_tokens: 16000,
      output_config: {
        effort: "medium",
        format: betaZodOutputFormat(QuizSchema),
      },
      ...FALLBACK,
      system: PROMPTS.quiz,
      messages: [
        {
          role: "user",
          content: `${header}\nSujet du quiz : ${topic}\nNombre de questions : ${count}`,
        },
      ],
    });
    const questions = (message.parsed_output?.questions || []).filter(
      (q) =>
        q.choices.length === 4 && q.answer_index >= 0 && q.answer_index < 4,
    );
    if (message.stop_reason === "refusal" || !questions.length) {
      return res
        .status(422)
        .json({ error: "Impossible de générer ce quiz. Reformule le sujet." });
    }
    res.json({ questions });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: errorMessage(error) });
  }
});

app.listen(PORT, () => {
  console.log(`Outil de révision prêt : http://localhost:${PORT}`);
  if (!process.env.ANTHROPIC_API_KEY && !process.env.ANTHROPIC_AUTH_TOKEN) {
    console.warn("Attention : ANTHROPIC_API_KEY n'est pas définie.");
  }
});
