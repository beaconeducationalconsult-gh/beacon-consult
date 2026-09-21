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
yarn test                 # the suite (408 tests, no Python, no browser)
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
Variables (**Production + Preview** — Vercel keeps them per environment, and a value scoped to
Preview only leaves the production build unconfigured), then **redeploy**: Vercel does not
rebuild because a variable changed.

A deploy built without them is green and serves the setup notice instead of the portal. That
notice prints the Vercel path, the names the build was missing and the redeploy step, and
`GET /build-info.json` on the deploy says the same thing in one request (`firebaseConfigured`,
`missingEnv`) — ask it before asking a browser.

**Still showing the notice after setting them?** It is one of four things: the variables are on a
*different Vercel project* (the project whose **Domains** tab lists your domain is the one that
serves it), they are scoped to **Preview/Development only** (look at the Environments column), you
redeployed a **preview** deployment (promoting one to production does not rebuild it, so it keeps
the environment it was built with), or the values were added after the build started. From your
machine, `npx vercel env ls` prints the names and their environments, and the failing deployment's
build log contains the line `Building WITHOUT Firebase config: …`.

If Vercel's settings keep not applying, commit the six values as **`.env.production`** instead:
Vite reads that file during `vite build`, so the repo carries the config and no project setting is
involved. Write it as **UTF-8** — a UTF-16 file is ignored silently — and check locally first with
`yarn build && node -e "console.log(require('./dist/build-info.json').firebaseConfigured)"`.
`docs/gotchas.md` has the long version.

**The Vite `VITE_` prefix must stay**, and Vercel's editor says so in a confusing way: it warns
that *"public prefixes expose values to the browser — if that's safe, change the variable to
Config."* It is safe, and it is the point. Vite only exposes variables named `VITE_…` to client
code, so the six values are **published in the JavaScript bundle** by design — Firebase's web
config is identifiers, not secrets, and its own documentation says so. Keep them as ordinary
(**Config**) variables rather than Sensitive/Secret ones: marking them secret changes nothing
about the bundle, keeps them out of local `vercel env pull`, and makes the deploy look
misconfigured. The security boundary is `firestore.rules` + `storage.rules` (published per
project) and the Authorized Domains list in Authentication — not the API key.

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

## Setting up a new Firebase project (console)

A brand-new project is empty in five separate places, and each one has its own error when it is
missed. Nothing here is done by the Vercel build: Firebase is configured in the console (or by the
CLI), and the app only ever *talks* to what already exists.

Do these in order. Steps 1–5 are console work; 6–7 are the two commands and the one bootstrap
that the repo can help with.

| # | Where | What to do | What breaks without it |
|---|---|---|---|
| 1 | [console.firebase.google.com](https://console.firebase.google.com) → **Add project** | Create the project (Analytics optional) and note its **project id** — the immutable one like `beacon-edu-consult-proj`, not the display name | — |
| 2 | **Build → Firestore Database → Create database** | **Native mode**, a location close to the users (multi-region `eur3`, or `nam5`), and **Production mode** — the real rules are published in step 6, and test mode is open to anyone with the project id | Every page fails with `unavailable` / "database does not exist" — the app has nothing to read. The location **cannot be changed later** |
| 3 | **Build → Authentication → Get started → Sign-in method → Email/Password → Enable** | Leave "Email link" off; add the site's domain under **Settings → Authorized domains** | Sign-up fails with `auth/operation-not-allowed`, and the app shows Firebase's raw message — this is the single most common "the app is broken" on a fresh project |
| 4 *(optional)* | **Build → Storage → Get started** | Only if you want the document library. **Cloud Storage for Firebase has required the Blaze plan (a linked billing account) since October 2024** — on the free Spark plan the console offers no bucket at all, and that is Google's rule, not this app's | Skipping it costs one feature: **Save to library** (P3-3). Everything else — curriculum, planners, exam papers, quiz decks, every export — works, downloads land in the browser's downloads folder, and the app says so instead of failing. Skip `make deploy-storage` too. Turning it on later is: enable Storage, `make deploy-storage`, reload — no code change. Two shapes of "no bucket" are handled: a bucket name in the config whose bucket does not exist (every request 404s) and no bucket name at all (`VITE_FIREBASE_STORAGE_BUCKET` empty, which `ref()` rejects outright). Leave the value as the console gave it either way |
| 5 | **Project settings → Your apps → Web (`</>`)** | Register a web app (nickname only — no hosting needed), then copy the six config values it prints | These are the `VITE_FIREBASE_*` values: Vercel → Settings → Environment Variables (**Production *and* Preview**) and the local `.env.local`. Without them the deploy is green and shows the setup notice |
| 6 | Repo, once | `firebase login` → `firebase use <project id>` → `make deploy-rules` (Firestore rules + 18 indexes) → `make deploy-storage` *(only if step 4 was done)*. No `firebase` on PATH, or it answers *"The system cannot find the path specified"*? Run the same commands through npx — `npx --yes firebase-tools@15.30.2 login`, and so on — or `npm install -g firebase-tools` and reopen the terminal | With production-mode rules unpublished, every read and write is denied: `permission-denied` on every page, and a sign-up that creates an Auth account but no profile doc. `firebase use` is what keeps `.firebaserc`, and therefore the CLI, on the project the app uses |
| 7 | The running app | Sign up once with your own email, then in **Firestore → users → (that uid)** set `role: "admin"` and `status: "approved"` | Sign-up forces `status: 'pending'`/`role: 'member'` and the rules forbid changing them from the client, so **nobody** can approve anyone until this row is done by hand. It is the bootstrap (P0-3) and must be repeated for each new school's first admin |

Order matters twice:

- **Step 6 before step 7.** Publishing the rules after a first sign-up leaves an Auth user with no
  `users/{uid}` document, which the app treats as "signed in but not a member" — the portal stays
  closed and there is nothing in the console to approve. If it happens anyway there is no need to
  delete the Auth user: open the portal and the account is offered **"Finish setting up your
  account"**, which writes the pending row the rules do allow.
- **Step 5 before the Vercel deploy** (P0-1), and the deploy **before** the rules (P0-2), because
  the rules gate list queries the older build does not make.

The project id is public — it ships in the client bundle — but it must be **the same** in three
places: the app's `VITE_FIREBASE_PROJECT_ID`, `.firebaserc` (what `make deploy-rules` follows) and
the console you publish from. `node scripts/verify_deploy.mjs` compares the first two and says so
if they drift (see gotchas.md).

## Deploying

Two separate concerns:

### 1. The app → Vercel
Vercel builds the Vite app and serves `dist/`. `vercel.json` has the SPA rewrite so every
path serves `index.html` (client-side routing). Push to the tracked branch → auto-deploy.

**Set the Production Branch.** Vercel deploys its *Production Branch* — `main` unless it is
changed — to the project's production domain; pushes to any other branch become preview
deployments under generated URLs. This repo's deployable line is
`arena/01a0af88-beacon-consult`, so point Production Branch at it (Settings → Git → Production
Branch) or that domain keeps serving `main`, which is still the old one-commit snapshot. The
failure is a quiet one: the app boots and every file that exists in both branches is identical,
while anything newer answers with the app shell because the rewrite catches it — which is why
`scripts/verify_deploy.mjs` compares each served file's size and shape with this checkout.

### 2. Firestore rules & indexes → Firebase CLI
**Not** handled by Vercel. After editing `firestore.rules` or `firestore.indexes.json`:

```
firebase deploy --only firestore:rules,firestore:indexes
```

`firebase.json` points at both files and `.firebaserc` pins the project
(`beacon-edu-consult-proj`), so no `--project` flag is needed. `make deploy-rules`
runs the command above. **A committed-but-undeployed rule change has no effect in
production.**

Pasting the rules into the Firebase console works too, and is the fastest way to unblock a
fresh project — but copy from this repo's `firestore.rules`, never from a chat message or a
design doc, or the console copy and the repo drift with nothing to detect it. Re-run the CLI
deploy the next time you touch the file.

## Verifying the deploy

```bash
make deploy-check URL=https://your-deploy.vercel.app     # scripts/verify_deploy.py
node scripts/verify_deploy.mjs -Url https://your-deploy.vercel.app   # Node only
.\scripts\deploy_check.ps1 -Url https://your-deploy.vercel.app       # the same, from PowerShell
```

Run it **before** telling anyone the deploy is ready, and again after every rules change. It is
also the fastest way to tell the two silent failures apart: a deploy built without the config
(the setup notice instead of the portal) and a deploy serving an older curriculum than this
checkout. `make preflight URL=…` is the same script.

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
