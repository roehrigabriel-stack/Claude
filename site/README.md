# Alfred Révision

Site de révision avec IA : explications de cours, fiches de révision et quiz, propulsés par l'API Claude.

## Comment ça marche

```
Navigateur (public/)  --->  Serveur Node (server.js)  --->  API Claude
   page + JavaScript         garde la clé API secrète        génère les réponses
```

- `public/` : la page web (HTML, CSS, JavaScript sans framework).
- `server.js` : le serveur Express. Trois routes :
  - `POST /api/explain` : conversation, réponse affichée au fil de l'eau (streaming).
  - `POST /api/sheet` : fiche de révision, en streaming aussi.
  - `POST /api/quiz` : quiz en JSON garanti conforme à un schéma (structured outputs).
- La clé API reste sur le serveur. Elle n'est jamais envoyée au navigateur.

Les consignes données à l'IA (les "system prompts") sont en haut de `server.js`, dans `PROMPTS`. C'est là qu'on change son comportement.

## Lancer en local

Il faut Node.js 20 ou plus et une clé API Anthropic (payante à l'usage, à créer sur https://platform.claude.com).

```bash
cd site
npm install
cp .env.example .env    # puis colle ta clé dans .env
npm run dev
```

Ouvre http://localhost:3000.

## Réglages (.env)

| Variable | Rôle |
|---|---|
| `ANTHROPIC_API_KEY` | Clé API, obligatoire |
| `SITE_PASSWORD` | Mot de passe demandé aux visiteurs. Vide = site ouvert |
| `DAILY_LIMIT` | Demandes max par jour et par adresse IP (100 par défaut) |
| `CLAUDE_MODEL` | Modèle utilisé (`claude-opus-5-5` par défaut) |

## Coût

Chaque demande est facturée sur la clé API. Avec `claude-opus-5-5` (4 $ par million de tokens en entrée, 20 $ en sortie), une fiche coûte de l'ordre de quelques centimes. `claude-haiku-5-5` est environ quarante fois moins cher, avec des réponses moins fines. Fixe une limite de dépense mensuelle dans la console Anthropic.

## Mettre en ligne

Le site est un serveur Node classique. Il se déploie sur un hébergeur comme Render ou Railway :

1. Créer un "Web Service" relié à ce dépôt GitHub.
2. Dossier racine : `site`. Build : `npm install`. Démarrage : `npm start`.
3. Ajouter `ANTHROPIC_API_KEY` et `SITE_PASSWORD` dans les variables d'environnement de l'hébergeur.

Mets toujours un `SITE_PASSWORD` en ligne : sans lui, n'importe qui peut utiliser le site et consommer ton crédit.
