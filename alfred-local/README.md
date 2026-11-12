# Alfred local

Une IA qui tourne entièrement sur ton appareil, dans le navigateur. Pas de Claude, pas de serveur, pas de clé API, rien à payer.

Tout tient dans un seul fichier : `index.html`.

## L'utiliser

Le plus simple : télécharge `index.html` et ouvre-le par double-clic dans Chrome ou Edge. Clique sur "Télécharger et démarrer", attends la fin du téléchargement du modèle, puis pose ta question.

- Le modèle (300 à 850 Mo) se télécharge une fois, puis reste dans le navigateur.
- Il faut une connexion Internet au démarrage (pour charger la bibliothèque et, la première fois, le modèle). Les questions et les réponses, elles, ne quittent jamais l'appareil.
- Sur un ordinateur récent, Alfred utilise la carte graphique et répond vite. Sans carte graphique accessible, il passe sur un modèle de secours, lent et moins bon.

## Comment ça marche

```
index.html
 ├─ la page (HTML, CSS, JavaScript)
 └─ le moteur : Transformers.js fait tourner un petit modèle de langage libre
    directement dans le navigateur (WebGPU pour la carte graphique, WebAssembly sinon)
```

- Modèles : LFM2 de Liquid AI (1,2 milliard ou 350 millions de paramètres) avec carte graphique, Qwen 2.5 d'Alibaba (500 millions) sur processeur. Ils sont téléchargés depuis Hugging Face.
- La liste des modèles est dans `MODELS`, et la consigne donnée à l'IA dans `systemPrompt()`, dans `index.html`.

## Ses limites

C'est un petit modèle, des centaines de fois plus petit que Claude. Il répond correctement aux questions simples, mais il se trompe parfois avec assurance, il calcule mal, et il oublie le début des longues conversations. Il n'a pas accès à Internet.

## Le mettre en ligne gratuitement

Comme c'est un simple fichier, n'importe quel hébergeur de sites statiques gratuit convient (GitHub Pages, Netlify, Cloudflare Pages). Pour GitHub Pages : crée un nouveau dépôt public qui contient seulement `index.html`, puis active Pages dans ses réglages.

Ne rends pas ce dépôt-ci public pour ça : il contient tes informations personnelles (`context/`, `CLAUDE.md`).
