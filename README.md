# Next on Acquired

A fan toy that guesses the next [Acquired](https://www.acquired.fm) podcast episode, with a
community board of everyone's locked-in picks.

- `index.html` – the whole site (styles + logic inline)
- `data.js` – all past episodes scraped from acquired.fm, with cover art embedded as data URIs
- `config.js` – Firebase web config (`null` = on-device preview mode, no shared board)
- `firestore.rules` – security rules for the shared board
- `scripts/scrape.py` – rebuilds `data.js` when a new episode drops

## How the community board works

- Visitors sign in anonymously with Firebase Auth (invisible to them). Their uid is their
  device token, so each browser gets exactly one pick and only that browser can change it.
- Picks live in `guesses/{uid}`. A single `board/tally` document holds the counts, labels and
  wildcards, updated with atomic increments, so rendering the board costs one read.
- Community odds derive from vote share once 8 or more people have locked in; before that the
  hand-written "house odds" show.
- A pick that isn't on the curated board becomes a wildcard and joins the reel for everyone,
  tagged with the submitter's nickname.

## Run locally

Any static server works, e.g.

```bash
npx serve .
```

With `FIREBASE_CONFIG = null` the board runs in preview mode (localStorage only).

## Deploy

The site is hosted on Firebase Hosting at https://next-on-acquired.web.app (GitHub Pages at
https://jptyralla.github.io/next-on-acquired/ mirrors `main` too).

```bash
npx firebase-tools deploy --only hosting
```

## Firebase setup (already done for this project)

1. Create a Firebase project at https://console.firebase.google.com
2. Build → Firestore Database → Create (production mode)
3. Build → Authentication → Sign-in method → enable **Anonymous**
4. Project settings → Your apps → Add web app → copy the `firebaseConfig` object into `config.js`
5. Publish the rules: paste `firestore.rules` into Firestore → Rules, or run
   `npx firebase-tools deploy --only firestore:rules` after `npx firebase-tools login`
6. Add your GitHub Pages domain (`<user>.github.io`) under Authentication → Settings →
   Authorized domains

## Refresh the episode list

```bash
python3 scripts/scrape.py
```
