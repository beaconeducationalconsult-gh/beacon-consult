# 8. Build, run & deploy

## Prerequisites

- **Node** 20+ and **Yarn 4** (Berry, `node-modules` linker). **Never use npm** — it would
  create a divergent lockfile.
- A `.env.local` with the Firebase web config (below).

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

`firebase.json` points at both files. There's no `.firebaserc` committed — pass
`--project <id>` if the CLI can't resolve the project. **A committed-but-undeployed rule
change has no effect in production.**

## Local verification loop

1. `yarn build && yarn preview`
2. Open the preview URL; check the manifest loads, the SW registers/activates, and
   curriculum/quotes are cached (DevTools → Application).
3. For data features you need a signed-in **approved** member (rules enforce it).
