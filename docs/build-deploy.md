# 8. Build, run & deploy

## Prerequisites

- **Node** 20+ and **Yarn 4** (Berry, `node-modules` linker). **Never use npm** — it would
  create a divergent lockfile.
- A `.env.local` with the Firebase web config (below).

## Updating a working copy

The deployable line is the branch `arena/01a0af88-beacon-consult` (it holds the whole portal;
`main` is still the old one-commit snapshot). A clone made with
`git clone --branch arena/01a0af88-beacon-consult …` tracks it, so an update is four commands —
same in PowerShell, Git Bash or a Unix shell:

```bash
git pull --ff-only        # fast-forward to the newest pushed commit
yarn install              # new dependencies, if the lockfile moved
yarn test                 # the suite (331 tests, no Python, no browser)
yarn dev                  # http://localhost:5199
```

`--ff-only` is deliberate: if it refuses, the checkout has local commits or edits, and a merge
or a stash is a decision to make on purpose rather than a surprise. `yarn install` is the only
step that matters after a *dependency* change; a data-only or page-only update still needs it
to be run at least once after pulling, because it is cheap and idempotent.

Two optional extras, both needing more than the app does:

- `yarn test:rules` — the Firestore/Storage permission matrix against the emulator. Needs a JVM
  (Java 21) and downloads `firebase-tools` plus the emulator jars on first run.
- `make check` — the full pre-deploy gate (lint + tests + curriculum validation + inventory +
  build). Needs `make` and Python 3; it is what CI runs.

`.env.local` is **not** in git: a fresh clone has none, and the app shows the setup notice
instead of the portal until the six `VITE_FIREBASE_*` values are there (copy the file from an
older checkout, or paste the values from the Firebase console).

## Environment variables

Vite embeds these at **build time** (they're public web-app config, not secrets, but the
build fails to talk to Firebase without them). In `.env.local` (gitignored):

```
VITE_FIREBASE_API_KEY=…
VITE_FIREBASE_AUTH_DOMAIN=…
VITE_FIREBASE_PROJECT_ID=…
VITE_FIREBASE_STORAGE_BUCKET=…
VITE_FIREBASE_MESSAGING_SENDER_ID=…
VITE_FIREBASE_APP_ID=…
```

Consumed in `src/firebase.js`. On Vercel, set the same keys in the project's Environment
Variables (Production + Preview).

## Scripts (`package.json`)

| Command | Does |
|---|---|
| `yarn dev` | Vite dev server (HMR). **No service worker** (dev). |
| `yarn build` | Production build → `dist/` |
| `yarn preview` | Serve the production build — use this to test PWA/offline |
| `yarn lint` | ESLint over the repo (keep it clean) |

`.claude/launch.json` defines `dev` (port 5199) and `preview` (port 4173) for tooling.

## Stack versions

- React **19.2**, React DOM 19.2, React Router **7**
- Vite **8** (Rolldown) + `@vitejs/plugin-react` + `@rolldown/plugin-babel`
  (`babel-plugin-react-compiler`)
- Tailwind CSS **v4** via `@tailwindcss/vite`
- Firebase **12**
- Tiptap **3** (`@tiptap/react`, `starter-kit`, underline/text-align/link/placeholder/
  character-count/image)
- jsPDF 4 + jspdf-autotable 5, docx 9, pptxgenjs 4
- `@vercel/analytics`

## Deploying

Two separate concerns:

### 1. The app → Vercel
Vercel builds the Vite app and serves `dist/`. `vercel.json` has the SPA rewrite so every
path serves `index.html` (client-side routing). Push to the tracked branch → auto-deploy.

### 2. Firestore rules & indexes → Firebase CLI
**Not** handled by Vercel. After editing `firestore.rules` or `firestore.indexes.json`:

```
firebase deploy --only firestore:rules,firestore:indexes
```

`firebase.json` points at both files and `.firebaserc` pins the project
(`beacon-educational-consu-8005e`), so no `--project` flag is needed. `make deploy-rules`
runs the command above. **A committed-but-undeployed rule change has no effect in
production.**

Pasting the rules into the Firebase console works too, and is the fastest way to unblock a
fresh project — but copy from this repo's `firestore.rules`, never from a chat message or a
design doc, or the console copy and the repo drift with nothing to detect it. Re-run the CLI
deploy the next time you touch the file.

## Verifying the deploy

```bash
make deploy-check URL=https://your-deploy.vercel.app
```

`scripts/verify_deploy.py` fetches `/build-info.json` (written by the Vite build: whether the
six `VITE_FIREBASE_*` values were present, the `bundleHash` of the curriculum it built, and the
commit), then `/`, `/curriculum/grades.json`, one per-subject schedules file, and `/sw.js`. It
fails loudly on the two silent killers: **a deploy built without Firebase config** (the app
shows the setup notice instead of the portal, and the build was green) and **a stale curriculum**
(a deploy whose `bundleHash` is not the one in this checkout). `make check` runs the offline half
of it.

The Firebase-backed flows still need a person: `docs/verification.md` is the step-by-step
checklist, with what each step is really testing.

## Local verification loop

1. `yarn build && yarn preview`
2. Open the preview URL; check the manifest loads, the SW registers/activates, and
   curriculum/quotes are cached (DevTools → Application).
3. For data features you need a signed-in **approved** member (rules enforce it).
