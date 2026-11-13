# Alfred local

Une IA qui tourne entièrement sur ton appareil, dans le navigateur, et qui peut chercher sur Internet. Pas de Claude, pas de serveur, pas de clé API, rien à payer.

Tout tient dans un seul fichier : `index.html`.

## L'utiliser

Télécharge `index.html` et ouvre-le par double-clic dans Chrome ou Edge. Choisis un modèle, attends la fin du téléchargement, puis pose ta question.

- Le modèle se télécharge une fois, puis reste dans le navigateur.
- Il faut une connexion Internet au démarrage (pour charger la bibliothèque et, la première fois, le modèle).
- Sur un ordinateur récent, Alfred utilise la carte graphique. Sans carte graphique accessible, il passe sur un modèle de secours, lent et bien moins bon.

## Ce qu'il sait faire

- **Trois tailles de modèle** : Standard (850 Mo), Avancé (1,9 Go, il réfléchit avant de répondre), Léger (300 Mo).
- **Internet** (bouton dans la zone de saisie) : Alfred cherche sur le web, lit les deux premières pages, répond et cite ses sources. La météo vient en direct d'Open-Meteo.
- **Calcul exact** : les opérations sont faites par une vraie calculatrice, pas par le modèle.
- **Plusieurs conversations**, gardées dans le navigateur, avec le bouton pour refaire ou copier une réponse.
- **Réglages** : ton prénom, ta ville pour la météo, des consignes permanentes.

## Comment ça marche

```
index.html
 ├─ l'interface (HTML, CSS, JavaScript, sans framework)
 ├─ le moteur : Transformers.js fait tourner un modèle de langage libre dans le
 │  navigateur (WebGPU pour la carte graphique, WebAssembly sinon)
 └─ Internet : avant de répondre, la page va chercher des informations
    et les glisse dans la question posée au modèle
       ├─ recherche web : DuckDuckGo, lu à travers le service Jina Reader
       ├─ lecture de pages : Jina Reader
       ├─ secours : Wikipédia
       └─ météo : Open-Meteo
```

- Modèles : LFM2.5 de Liquid AI avec carte graphique, Qwen 2.5 d'Alibaba sur processeur, téléchargés depuis Hugging Face.
- Dans `index.html` : la liste des modèles est dans `MODELS`, la consigne donnée à l'IA dans `systemPrompt()`, et toute la partie Internet dans `gather()`.

## Vie privée

Sans Internet, rien ne quitte ton appareil. Quand Internet est activé, ta question (ou la recherche qu'Alfred en tire) part vers DuckDuckGo via Jina, Wikipédia ou Open-Meteo. Les conversations sont stockées dans le navigateur, nulle part ailleurs.

## Ses limites

- Ce sont de petits modèles, bien plus petits que Claude. Ils se trompent parfois avec assurance, même avec des sources sous les yeux : vérifie ce qui compte.
- La recherche passe par des services gratuits sans clé. Ils peuvent ralentir, limiter le nombre de demandes ou changer. Dans ce cas Alfred répond sans Internet ou se rabat sur Wikipédia.
- Le modèle Avancé pèse 1,9 Go et demande une bonne carte graphique.

## Sur téléphone

Un téléphone ne peut pas lancer Alfred depuis le fichier : les aperçus (application Fichiers, pièce jointe, application Claude) bloquent l'accès à Internet dont la page a besoin pour charger le modèle. Il faut l'ouvrir depuis une adresse web dans Safari ou Chrome, donc le mettre en ligne (voir ci-dessous).

Sur téléphone, choisis le modèle Léger (300 Mo). Il faut un téléphone récent : sur iPhone, iOS 26 ou plus pour que Safari donne accès à la carte graphique. Sans elle, le modèle de secours (790 Mo) risque de dépasser la mémoire du téléphone.

## Le mettre en ligne gratuitement

Comme c'est un simple fichier, n'importe quel hébergeur de sites statiques gratuit convient. Avec GitHub Pages :

1. Sur github.com, crée un nouveau dépôt **public**, par exemple `alfred`.
2. Dans ce dépôt : Add file, Upload files, choisis `index.html`, puis Commit changes.
3. Settings, Pages, Source : "Deploy from a branch", branche `main`, dossier `/ (root)`, Save.
4. Après une minute environ, la page est en ligne à l'adresse `https://TON-PSEUDO.github.io/alfred/`.

Ne rends pas ce dépôt-ci public pour ça : il contient tes informations personnelles (`context/`, `CLAUDE.md`).
