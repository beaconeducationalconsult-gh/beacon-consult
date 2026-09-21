# SKILL.md — Building **Beacon Consult** from zero

*A complete, start-to-finish guide for someone who has never seen this project. Every command
here was run against this repository; every error in Part 17 is one this project actually hit.*

---

## How to read this

The guide is written in **phases**. Each phase ends with a *Done when* checklist — if the check
fails, do not continue to the next phase; the next one assumes the last one worked.

| Phase | You will | Time | Needs |
|---|---|---|---|
| **0** | Understand what you are building | 15 min | nothing |
| **1** | Run the app on your machine, with no cloud account | 30 min | Node, Git, Yarn |
| **2** | Create the Firebase project (the "backend") | 30 min | a Google account |
| **3** | Connect the app to it locally | 15 min | Phase 2 |
| **4** | Become the first administrator, and sign in | 20 min | Phase 3 |
| **5** | Publish the security rules and indexes | 20 min | Phase 4, Node |
| **6** | Put it on the internet (Vercel) | 30 min | Phase 5 |
| **7** | Verify the deploy end to end | 45 min | Phase 6 |
| **8** | Work on the data (curriculum, questions, books) | open-ended | Python |

Two rules of thumb before you start:

1. **Never mix package managers.** This project is Yarn 4. `npm install` here creates a second,
   conflicting lockfile and a broken `node_modules`. Use `yarn` for JavaScript, `pip` for Python.
2. **The order in Phases 4–5 matters** (rules before sign-up). Where it does, the guide says why,
   so you can tell when you are safe.

If you are on Windows, every command is given in PowerShell form, with the Unix equivalent in
parentheses where it differs.

---

## Phase 0 — What you are building

Beacon Consult is **two products sharing one dataset**:

1. **The portal** — a members-only web app for Ghanaian basic-school teachers (KG1–B9). It runs
   entirely in the browser and is deployed as static files. Teachers browse the NaCCA
   Standards-Based Curriculum, write schemes of learning and lesson plans, author questions,
   build exam papers and quizzes, keep notes and articles, track progress, and export everything
   as Word / PDF / PowerPoint.
2. **The books** — Word workbooks and textbooks generated offline from the same data by Python
   scripts under `scripts/` and `seed/`. They are the sellable artefacts; they are not part of
   the web app.

### The stack, and what each piece does

| Layer | Technology | Where it runs |
|---|---|---|
| UI | React 19, React Router 7 | the browser |
| Build tool | Vite 8 (Rolldown) | your machine, and Vercel at deploy time |
| Styling | Tailwind CSS 4 (via `@tailwindcss/vite`) | build time |
| Auth / data / files | Firebase 12 — Authentication, Firestore, Storage *(optional)* | Google's cloud |
| Exports | jsPDF 4 + jspdf-autotable, `docx` 9, pptxgenjs 4, Tiptap 3 (rich text) | the browser |
| Curriculum data | static JSON in `public/curriculum/`, built by Python | your machine, committed to git |
| Offline | a service worker (`public/sw.js`) + Firestore's own cache | the browser |
| Tests | Vitest (+ Firebase emulator for the rules suite) | your machine, and CI |
| CI | GitHub Actions (three jobs) | GitHub |
| Hosting | Vercel (static build of `dist/`) | Vercel |

### There is no server to run

This is the single most important thing to understand, because it changes what "setup" means:

- **Firebase is the backend.** There is no API to write, no database to install, no server to
  start. Firestore is queried *directly from the browser*, and `firestore.rules` — a file in this
  repo that you publish to your project — is what enforces who may read and write what.
- **The Python scripts are a build-time pipeline, not a server.** They read the NaCCA source PDFs
  and curriculum databases in `data/`, and write the JSON bundle in `public/curriculum/`. They run
  on your machine when the data changes. Nothing imports them at runtime, and `requirements.txt`
  deliberately has no web framework in it.
- **The curriculum works offline because it is static files**, not because of a cache server.

So the "backend setup" of this project is: create a Firebase project, publish two rules files and
an index list, and (optionally) point the app at a Storage bucket. Everything else is front-end.

### What the finished portal can do

Reachability in brackets (`/portal/...` means it needs a signed-in, approved member):

- **Curriculum browser** — every served subject-grade, strand, sub-strand and indicator, with the
  official NaCCA codes, offline. `/portal/curriculum`
- **Schemes of learning** (weekly forecasts) — pick grade + subject + term, get the term's
  scheduled weeks pre-filled, edit, export to Word/PDF. `/portal/forecasts`
- **Lesson plans** — written against a specific indicator, with teaching phases, a resource list,
  assessment notes; export to Word/PDF; save to your library. `/portal/plans`
- **Question bank** — 1,000+ ready questions covering 100% of mathematics indicators B2–B9, plus
  your own; paged, searchable, importable from the built-in starter bank. `/portal/questions`
- **Exam paper builder** — compose a BECE-style paper to a target mark (30/50/60), scoped to a
  term, with sections A/B/C, a marking scheme, and student + teacher PDFs. `/portal/questions/exam`
- **Quiz slideshow** — turn selected questions into a PPTX. `/portal/questions/quiz`
- **Question generator** — parameterised question templates. `/portal/questions/generate`
- **Slide lessons** — deck outlines built from a week's scheduled lessons. `/portal/slides`
- **Study notes** — private drafts or shared notes, with comments. `/portal/notes`
- **Articles** — long-form posts, public or members-only. `/portal/articles`
- **Vacancies** — job adverts, publishable to the public site. `/portal/vacancies`
- **Teaching models** — five interactive mathematics models. `/portal/models`
- **My library** — keep generated documents in the cloud and open them later *(needs Storage)*.
  `/portal/library`
- **Progress**, **term calendar**, **quote of the day**, **member directory**, **search**,
  **profile**.
- **Public pages, no login**: landing, articles, vacancies, quotes, academic calendar, sign-up,
  sign-in.

The features are described in more depth in `docs/features.md`; this guide tells you how to build
and run them.

---

## Phase 1 — Run it on your machine (no cloud account yet)

You can complete this phase with no Firebase project at all: the app will show a setup notice
instead of the portal, which is the correct behaviour and proves the toolchain works.

### 1.1 Install the tools

| Tool | Version | Why | Install |
|---|---|---|---|
| **Git** | any recent | get the code | <https://git-scm.com/downloads> |
| **Node.js** | **22 or newer** | runs the app, the tests and the build | <https://nodejs.org> (LTS) |
| **Yarn** | **4.9.4** — do not install it by hand | the project's package manager | see below |
| **Python** | 3.11+ | the data pipeline and the document generators | <https://www.python.org/downloads/> |
| **make** | optional | `make check` and friends | Windows: use `python3 scripts/...` directly, or install `make` via Git Bash / WSL |
| **Java 21** | optional | only the Firestore-emulator rules suite (`yarn test:rules`) | any JDK 21 (Temurin) |

Yarn 4 comes from **Corepack**, which ships with Node:

```powershell
corepack enable          # once per machine; makes `yarn` the version package.json pins
node -v                  # expect v22.x or newer
yarn -v                  # expect 4.9.4 once you are inside the project folder
```

> If `yarn -v` prints **1.22.x**, you have the old global Yarn and Corepack was not enabled.
> Run `corepack enable`, then close and reopen the terminal (PATH changes do not reach an open
> window). If a machine refuses to cooperate, any command in this guide that starts with `yarn`
> can be run as `corepack yarn …` instead.

Python packages for the data pipeline are separate and optional until Phase 8:

```powershell
pip install -r requirements.txt      # currently: python-docx, for the Word generators
```

### 1.2 Get the code

The deployable line of this project is the branch `arena/01a0af88-beacon-consult`. `main` holds an
older one-commit snapshot, so clone the branch explicitly:

```powershell
git clone --branch arena/01a0af88-beacon-consult https://github.com/beaconeducationalconsult-gh/beacon-consult.git
cd beacon-consult
git log --oneline -3        # confirm you are on the arena branch
```

If you already have a clone on another branch:

```powershell
git fetch origin arena/01a0af88-beacon-consult
git checkout arena/01a0af88-beacon-consult
git pull --ff-only
```

### 1.3 Install dependencies and start the dev server

```powershell
yarn install          # downloads ~420 packages into node_modules/
yarn dev              # starts Vite on http://localhost:5199
```

Open <http://localhost:5199>. With no Firebase configuration you will see **"Beacon is not
configured yet"** — that is Phase 3's job, and the notice tells you which values are missing. The
important part is that Vite compiled, React mounted, and no red error is on screen.

Two other commands you will use constantly:

```powershell
yarn build            # production build into dist/  (also writes dist/build-info.json)
yarn preview          # serves dist/ on http://localhost:4173
yarn lint             # ESLint, including the React Compiler rules — must stay clean
yarn test             # the unit + contract suite (~421 tests, no browser, no Python)
```

**Service workers only exist in `yarn preview`**, never in `yarn dev`. Anything offline-related
must be tested against the preview server. That is why both ports are pinned: dev `5199`,
preview `4173` (they are declared in `vite.config.js` and `.claude/launch.json`).

### 1.4 Know your way around the tree

```
beacon-consult/
├── src/                  the portal (React) — the app you deploy
│   ├── main.jsx          entry: renders SetupNotice when Firebase config is absent
│   ├── App.jsx           every route, and the portal's approval gate
│   ├── firebase.js       initialises Firebase from the VITE_FIREBASE_* build variables
│   ├── pages/            one file per screen (42 of them)
│   ├── components/       shared UI — 18 files (Sidebar, DataError, PendingApproval, SaveToLibrary …)
│   ├── hooks/            useCollection / usePagedCollection / useCurriculum / useLibrarySave
│   ├── context/          AuthContext (who am I, approved?) and ToastContext
│   └── lib/              pure logic — 25 modules: exam papers, exports, calendar, starter bank, profile
├── public/               served as-is: curriculum bundle, quotes, sw.js, manifest
│   └── curriculum/       39 MB of static JSON — the offline dataset the app reads
├── data/                 the SOURCE data (curriculum DBs, lessons, questions, audits)
├── scripts/              Python: audit the data, build the bundle, generate books
├── seed/                 Python: book skeletons
├── legacy/               the retired NCOS app — reference only, nothing imports it
├── docs/                 the long-form documentation (doc map in Part 19)
├── firestore.rules       who may read/write Firestore — you publish this
├── storage.rules         the same for uploaded documents (only if you enable Storage)
├── firestore.indexes.json  the composite indexes the app's queries need
├── firebase.json         tells the Firebase CLI where those three files are
├── .firebaserc           which Firebase project the CLI deploys to
├── vercel.json           SPA rewrite + cache headers for the deploy
├── Makefile              the task runner (make check, make build-curriculum, …)
└── SKILL.md              this file
```

**Done when:** `yarn dev` serves the setup notice at <http://localhost:5199>, `yarn test` passes,
and `yarn lint` is clean.

---

## Phase 2 — Create the Firebase project (the backend)

Firebase is the whole backend: accounts, database, and (optionally) file storage. Nothing here is
done by Vercel or by the build; a deploy cannot create these for you, and each missing piece has
its own error message later.

Open <https://console.firebase.google.com> and do these in order. **Steps 2.1–2.4 are console
work; 2.5 is the only one that needs the command line.**

### 2.1 Create the project

**Add project** → name it (the display name can be anything: `beacon-edu-consult`) → Analytics is
optional (this app does not use it) → Create.

Note the **project id** — the immutable one in the URL and under ⚙︎ *Project settings*, like
`beacon-edu-consult-proj`. It is *public* (it ships in the browser bundle) but it must be **the
same** in three places, or you will publish your rules to a project your app never talks to:

1. the app's `VITE_FIREBASE_PROJECT_ID` (Phase 3),
2. `.firebaserc` in this repo (what `make deploy-rules` follows),
3. the console you are looking at.

### 2.2 Create the Firestore database

**Build → Firestore Database → Create database**

- **Native mode** (not Datastore mode — the app uses Firestore's document API).
- **Location**: pick one close to your users and never think about it again —
  **the location cannot be changed later**. For Ghana, a multi-region such as `eur3` is the usual
  choice; `nam5` is equally valid.
- **Production mode** (not test mode). Test mode leaves the database open to anyone with the
  project id until it expires; your real rules arrive in Phase 5.

*If you skip this:* every page fails with `unavailable` / "database does not exist".

### 2.3 Enable email/password sign-in

**Build → Authentication → Get started → Sign-in method → Email/Password → Enable.**
Leave *Email link* off — the app uses plain email + password and never sends verification mail.

Then **Authentication → Settings → Authorized domains** and add:

- `localhost` (already there, for local development),
- your production domain, e.g. `beacon-edu-consult.vercel.app` (add it now if you know it),
- any custom domain you plan to use.

*If you skip this:* sign-up fails with `auth/operation-not-allowed` and the app now tells you so
by name. This is the most common "the app is broken" on a fresh project, and it takes ten seconds
to fix.

### 2.4 Register the web app and copy its config

**Project settings (⚙︎) → Your apps → Web (`</>`)** → give it a nickname (`beacon-web`) → Register.
Hosting is *not* needed (Vercel serves the app). Firebase then prints a `firebaseConfig` object:

```js
const firebaseConfig = {
  apiKey: "AIza…",
  authDomain: "your-project-id.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project-id.firebasestorage.app",   // may be .appspot.com on older projects
  messagingSenderId: "1024…",
  appId: "1:1024…:web:…",
}
```

Those six values are the `VITE_FIREBASE_*` variables in Phase 3. They are **identifiers, not
secrets**: they are published in the JavaScript bundle by design, which is why the security lives
in the rules and in the Authorized Domains list, never in the key.

### 2.5 Storage — *optional, and can be skipped*

**Build → Storage → Get started** creates the bucket the *document library* ("Save to library",
`/portal/library`) uses.

You can skip it. Since **October 2024** Cloud Storage for Firebase requires the pay-as-you-go
**Blaze** plan (a linked billing account), even at zero usage — that is Google's rule, not this
app's. On the free Spark plan the console simply offers no bucket. Skipping Storage costs exactly
one feature; curriculum, planners, exam papers, decks and every export work without it, files
land in the browser's downloads folder, and the app says so instead of failing:

> *"Keeping documents in the portal needs Firebase Storage, which this project does not have
> enabled. The download above is yours to keep."*

**If you do enable it**, you must also publish `storage.rules` (Phase 5) — without them every
upload is denied. Leave the `storageBucket` value exactly as the console gave it either way.

### 2.6 Point the repository at your project

The Firebase **CLI** publishes the rules; `.firebaserc` tells it which project. Edit the file so
its `default` matches your project id:

```json
{
  "projects": {
    "default": "your-project-id"
  }
}
```

Or let the CLI do it (Phase 5, after `login`): `firebase use your-project-id`.

> Two files, two tools, one project: `.env.local` (Vite, gitignored, per machine) and
> `.firebaserc` (the CLI, committed). If they disagree, `make deploy-rules` publishes the rules to
> a project your app never reads — a *successful deploy to the wrong database*, which is a very
> expensive kind of silence. `node scripts/verify_deploy.mjs` (Phase 3.3) compares them and refuses
> to call it a pass.

**Done when:** the project exists, Firestore is created in Native mode, Email/Password is enabled,
a web app is registered (its config copied somewhere safe), and `.firebaserc` names the project.

---

## Phase 3 — Connect the app to your project (local)

### 3.1 Create `.env.local`

`.env` files are gitignored: a fresh clone has none, and the app shows the setup notice until the
six values exist. Copy the template and fill in the six values from Phase 2.4:

```powershell
Copy-Item .env.example .env.local
notepad .env.local
```

```
VITE_FIREBASE_API_KEY=AIza…
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project-id.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=1024…
VITE_FIREBASE_APP_ID=1:1024…:web:…
```

Rules that are not obvious:

- **Keep the `VITE_` prefix.** Vite only inlines variables with it; renaming breaks the app.
- **No quotes, no spaces around `=`** (Vite tolerates quotes, but half the tools in this project
  do not).
- **Do not write it with PowerShell's `>` or `Out-File`.** Windows PowerShell writes those as
  **UTF-16**, and read as UTF-8 the file is full of NUL bytes — every key "disappears" and the app
  behaves as if it has no config, on a machine where you can see the values in the file. Use an
  editor, or:
  `Set-Content .env.local -Encoding utf8 -Value @('VITE_FIREBASE_API_KEY=…', …)`.
- **Restart `yarn dev` after editing it.** Vite reads env files at startup.

### 3.2 Start the app and sign in

```powershell
yarn dev
```

The setup notice is gone; you get the public site. Sign up at `/signup` (or sign in). You will
land on **"Awaiting approval"** — correct, and Phase 4 is how you get past it.

> **If sign-up reports a permission error**, that is expected at this point in the guide: the
> database is in production mode with no rules published yet, so the *account* is created in
> Authentication but the *membership row* in Firestore is refused. The app detects this and offers
> **"Finish setting up your account"** on the portal screen; nothing is lost. Phase 5 removes the
> cause.

### 3.3 Check the local configuration like a deploy

```powershell
node scripts/verify_deploy.mjs -SkipBuild
```

This is the same pre-flight the deploy uses, stopping before the network checks. It reports:

- the branch and commit you are on (and warns about uncommitted work),
- whether `.env.local` has all six values — and, if not, the **names** of the keys it did find,
  never the values,
- whether `.firebaserc` pins the same project the app uses,
- what the last build embedded.

**Done when:** the app runs without the setup notice, you have signed up an account, and
`node scripts/verify_deploy.mjs -SkipBuild` says the config is complete and the projects match.

---

## Phase 4 — Become the first administrator

New accounts are created **pending** on purpose. `src/pages/SignUp.jsx` writes
`status: 'pending'` and `role: 'member'`, and `firestore.rules` makes those the *only* values a
client may write — a client that could approve itself would walk past every other rule in the
file. So the first administrator is created **by hand, once, in the console**:

1. Sign up in the app with the email you want to use as the school's administrator.
2. Firebase console → **Firestore Database → Data → `users`** → open the document whose id is your
   uid (the uid is shown in **Authentication → Users**, and it *is* the document id).
3. Edit the document and set:
   - `role` = `"admin"`
   - `status` = `"approved"`
   Save. Do not change anything else.
4. Reload the app: the portal opens.

From then on, you approve everyone else from **`/portal/members`** — no console needed. This
bootstrap has to be repeated once for each new school's first administrator; it is the only way in,
by design (see `docs/security.md`).

### The order that matters (and the recovery if you break it)

**Publish the rules (Phase 5) before a real sign-up, and sign up before you need an admin.**

- Sign-up is **two writes**: Authentication creates the account, then Firestore stores the
  membership row. If the rules are not published yet, the first succeeds and the second is
  refused — you end up signed in with no membership.
- The app recognises that state (a signed-in user with no `users/{uid}` document) and offers
  **"Finish setting up your account"**, which creates the pending row the rules *do* allow. You do
  not have to delete the Auth user and start again.
- If you instead approve first and publish rules later, you are fine — but an old client whose list
  pages query un-filtered will see `permission-denied` once the new rules are live. Publish after
  the new build is deployed, not before (Phase 6 then Phase 5 when updating an existing site).

**Done when:** you can open `/portal` and every sidebar link loads, and `/portal/members` shows
the pending accounts you expect.

---

## Phase 5 — Publish the security rules and indexes

Three files in this repo are the *entire* enforcement layer. A committed-but-unpublished rule does
nothing — the console is what counts.

| Publish | File | What it gates |
|---|---|---|
| Firestore rules | `firestore.rules` (~560 lines) | every read and write: users, content, visibility, likes, progress, the document-library records |
| Firestore indexes | `firestore.indexes.json` (18 composite indexes) | the *list* queries: without them Firestore answers `failed-precondition` and the page shows nothing |
| Storage rules *(only if Storage is enabled)* | `storage.rules` | uploads under `generated/{uid}/…`, owner-only, ≤ 8 MiB |

### 5.1 Install the CLI once

The Firebase command-line tool is not a project dependency; run it through `npx` so there is
nothing to install globally and no PATH to repair:

```powershell
npx --yes firebase-tools@15.30.2 login
npx --yes firebase-tools@15.30.2 use your-project-id     # writes .firebaserc
```

A browser opens for `login`; `use` prints the project it selected. (If you prefer a global
install: `npm install -g firebase-tools`, then reopen the terminal. If `firebase` answers
*"The system cannot find the path specified"*, your PATH has a stale shim — the `npx` form above
sidesteps it.)

### 5.2 Publish

```powershell
npx --yes firebase-tools@15.30.2 deploy --only firestore:rules,firestore:indexes
```

If you enabled Storage (Phase 2.5), add it:

```powershell
npx --yes firebase-tools@15.30.2 deploy --only storage
```

`firebase.json` points the CLI at the three files, so no paths are needed. With `make` available
the same commands are `make deploy-rules` and `make deploy-storage`.

Expect `✔ Deploy complete!` and a list of the files it compiled. Indexes take a minute or two to
build in the background — the console shows them as *Building*.

Four things you may meet here, all covered in Part 15 (rows 21–24):

- `HTTP Error: 400, this index is not necessary` — an entry in `firestore.indexes.json` with a
  single field. It aborts the **whole** indexes deploy, so nothing else gets created either;
  delete that entry and re-run. This command publishes the rules *before* the indexes, so a
  failure here leaves the rules new and the indexes missing — a half-deployed project. Re-running
  is safe and idempotent.
- `[W] Unused function: …` — a rule helper nothing calls.
- `[W] Invalid function name: exists` — the same warning seen from inside that unused function's
  body; both disappear with the unused function.

### 5.3 Test the rules without touching production

The rules have their own test suite, which runs against the Firebase **emulator** (needs Java 21,
downloads the emulator on first run):

```powershell
yarn test:rules        # 97 checks: pending member refused, un-filtered list denied, upload caps…
```

This is the only check `make check` cannot run, which is why CI runs it in its own job. Keep it
green: it is the suite that caught a real hole (a rule that denied every library save) before it
reached a teacher.

**Done when:** `deploy` reported success, the indexes finish building, `/portal/members` loads
without a `failed-precondition` error, and `yarn test:rules` passes.

---

## Phase 6 — Put it on the internet (Vercel)

The app is static: Vercel builds `dist/` and serves it. Firebase stays where it is.

### 6.1 Import the repository

<https://vercel.com/new> → import `beacon-consult` → leave the build settings alone
(`vercel.json` already carries the SPA rewrite and cache headers) → Deploy. The values the app needs
are committed (Phase 6.2 explains), so the first deploy should come up ready to sign in; if it shows
the setup notice instead, `GET /build-info.json` on it says what the build was missing.

### 6.2 Set the six environment variables

**Settings → Environment Variables** → add each of the six `VITE_FIREBASE_*` names and values from
Phase 2.4, for **Production *and* Preview** (Vercel keeps them per environment; setting only
Production leaves every preview deploy unconfigured).

Vercel's editor warns: *"Remove the public framework prefix to keep this value private… if that's
safe, change the variable to Config."* Save it as an ordinary **Config** variable and keep the
`VITE_` prefix:

- the prefix is what makes Vite inline the value into the browser bundle — removing it makes the
  app read `undefined` and show the setup notice;
- these values are **public by design** (Firebase's own docs say so); the security boundary is the
  rules you published in Phase 5, plus the Authorized Domains list;
- marking them *Sensitive* changes nothing about the bundle and breaks `vercel env pull`, which is
  how a teammate would configure their machine from Vercel.

This is also the step people *think* they have done. Two things to know before you move on:

1. **A variable belongs to the environment it is enabled for.** Set them for **Production** and
   **Preview** (tick both boxes). A value that lives only under Preview leaves the production
   build — the one on your domain — unconfigured.
2. **Changing a variable does not rebuild anything.** Vercel builds with the values that exist at
   build time, so after adding or editing one you must *Deployments → ⋯ → Redeploy* (or push a
   commit). Reloading the domain proves nothing; the build has to run again.

If you skip this, the deploy is **green** and the site shows the setup notice instead of the
portal. To save yourself the round trip: `GET https://<your-domain>/build-info.json` answers in
one request whether the build had the values, and names any that were missing
(`firebaseConfigured`, `missingEnv`). The notice prints the same answer to whoever opens the
site — on a real domain it lists the exact missing names, the Vercel path and the redeploy step
(Part 15, row 23).

**You do not have to do 6.2 at all.** The six values are also committed as source in
`src/firebaseConfig.js`, and `src/firebase.js` falls back to them for anything the environment does
not supply — so a build, in Vercel or on your machine, always has a working config, and no dashboard
state can break it. A non-blank environment value still wins (that is how you point a deploy at a
different Firebase project without a code change), and a *blank* one counts as absent and falls back
to the file. Fill 6.2 in only if you prefer the values in the dashboard; **delete** any variable you
leave empty, and read the build log if in doubt — it names blank ones and says where a build's config
came from, as does `configSource` in `/build-info.json`.

If you do set them and the notice is still there: they are on a *different Vercel project* (the one
whose **Domains** tab lists your address is the one that matters), or scoped to
**Preview/Development only** (read the **Environments** column), or you redeployed a **preview**
deployment (promoting a preview does not rebuild it, so it keeps the environment it was built with),
or they were added after the build began. `npx vercel env ls` prints the names and their
environments. `docs/gotchas.md` has the long version, including the two silent traps that killed a
committed `.env.production`: a BOM from PowerShell hides the first line, and a blank variable in the
environment shadows a file value.

### 6.3 Set the Production Branch — the one setting everybody misses

**Settings → Git → Production Branch.**

Vercel deploys its **Production Branch** (`main` by default) to the production domain; pushes to
any other branch become *preview* deployments with generated URLs. This repository's deployable
line is **`arena/01a0af88-beacon-consult`**.

Leave it on `main` and the failure is beautifully deceptive: the domain boots, `/` serves the
shell, and every file that exists in both branches — like `grades.json` — is byte-identical. What
is missing is everything *newer*: `/build-info.json` and `/curriculum/schedules/*` come back as
the app shell, because the SPA rewrite answers every unknown path with `index.html`.

Two ways to be correct, pick one:

- **Point Production Branch at `arena/01a0af88-beacon-consult`** (one dropdown, no git work), or
- **Publish the arena branch to `main`** and let Vercel deploy `main` as it does now.

Then **Redeploy**.

### 6.4 Deploy from the start

Vercel builds on every push. A local pre-flight before you push saves a round trip:

```powershell
yarn build                                       # writes dist/build-info.json
node scripts/verify_deploy.mjs -SkipBuild        # config + project ids + what the build embedded
```

**Done when:** <https://your-deploy.vercel.app> shows the portal (or the sign-in page), and the
*Vercel Preview Comments* check run on your latest commit has gone green.

---

## Phase 7 — Verify it, from the outside and by hand

A green build proves nothing about rules, indexes, or the service worker. Verification is two
layers: a script that cannot lie about the deploy, and a checklist only a person can walk.

### 7.1 The automated half

```powershell
node scripts/verify_deploy.mjs -Url https://your-deploy.vercel.app/
```

(Peers: `make deploy-check URL=…` and `scripts/verify_deploy.py` — same checks, same exit code;
`.\scripts\deploy_check.ps1` is a thin PowerShell wrapper. `src/deployCheck.test.js` fails if the
two implementations drift apart.)

It fetches the deploy and fails with an explanation for each of these:

| Check | Catches |
|---|---|
| `GET /build-info.json` → `firebaseConfigured` | A deploy built **without** the six values: green build, setup notice for every teacher |
| `build-info.json` → `bundleHash` vs `public/curriculum/_BUILD_REPORT.json` | A deploy serving an older curriculum than the checkout |
| `build-info.json` → `projectId` vs your `.env.local` | A deploy talking to a different Firebase project than your machine |
| `GET /` returns the SPA shell | A broken rewrite (every deep link 404s) |
| `/curriculum/grades.json` and `/curriculum/schedules/b1-mathematics.json` — status, shape **and size** vs this checkout | A rewrite swallowing the bundle, and the wrong-branch deploy (a 200 that is actually `index.html`) |
| `GET /sw.js` reads `bundleHash` | An old build whose service worker would keep a stale cache |

### 7.2 The human half

`docs/verification.md` is the checklist: 27 numbered steps, each with *what it is testing* (which
rule, index or cache it exercises). The short version of the order:

1. **Sign up → approve → publish content** with a second account (step 1–3).
2. **Scheme** — create from a term's scheduled weeks, reopen, edit, delete (4–7).
3. **Lesson plan** — from a curriculum indicator, export Word and PDF (8–11).
4. **Private drafts** — a `visibility: 'private'` note must not appear to another member (12–16).
5. **Question bank** — author questions, page to the end, build a paper and a deck (17–20).
   Includes 17a: import the **starter bank** (Mathematics B4 → 187 questions, 71/71 indicators).
6. **Exam builder** (19a–19e) — B2 at 50 marks composes **exactly 50** with all three sections;
   the term line reads 100%; drop a question; export both PDFs; save to library *(Storage only)*.
7. **Progress / calendar / comments** (21–23).
8. **Offline** — in `yarn preview`: browse, then DevTools → Network → Offline → reload; the app
   must boot and show the curriculum you browsed (24–26).
9. **After a curriculum rebuild** — a returning browser picks up new data without "clear site
   data" advice (27).

Drive it in an **ordinary member account**, not the admin you created in Phase 4. Admins pass
branches ordinary members do not — that is exactly how the un-filtered-list bug reached
production once.

### 7.3 When a step fails

Start from the symptom; the two Firestore codes point at completely different repairs, and the app
now prints which one it is:

| Symptom | Cause | Fix |
|---|---|---|
| `permission-denied` on a whole list | Published rules are older than the build, or the account is not approved | Re-publish `firestore.rules`; check the member's `status` in `/portal/members` |
| `failed-precondition` (the page shows a **Create the missing index** button) | A composite index is missing | Click the link → Create index → wait a minute. `src/firestoreIndexes.test.js` makes this impossible for a shipped query; if it fires, a query was added without its index |
| Setup notice instead of the portal | The *deploy* was built without `VITE_FIREBASE_*` (a local build can be fine) | `node scripts/verify_deploy.mjs -Url …`; set them on Vercel for Production **and** Preview; redeploy |
| Empty grade/subject dropdowns | The curriculum bundle is not being served | Same script — it fetches the very files the dropdowns need |
| `/build-info.json` or `/curriculum/schedules/*` returns HTML | Production is deploying a **different branch** | Phase 6.3 |
| Old data in a returning browser | Service worker serving the old cache | Compare the deploy's `bundleHash` with `public/curriculum/_BUILD_REPORT.json` |
| Everything works for the admin, not for a member | The un-filtered-list bug, or an index only the member's query path needs | Always test as a member |
| `storage/unknown` on Save to library | The project has no Storage bucket | Expected without Blaze; the app says so. See Phase 2.5 |

Record what you saw before fixing: the URL, the account's role/status, and the error code.

**Done when:** every line of the pre-flight is green and the checklist section 2 passes for an
ordinary member.

---

## Phase 8 — Work on the data (curriculum, questions, books)

This phase is for changing *what the app knows*, rather than what it does. Nothing here needs
Firebase.

### 8.1 The three layers

| Layer | Where | What it is | Committed? |
|---|---|---|---|
| **L1 — curriculum** | `data/curriculum/*.json` | the audited extraction of the NaCCA curriculum: 84 subject-grade databases, 4,040 indicators, plus human-readable summaries | yes |
| **L2 — lessons** | `data/lessons/*.json` | a teaching template filled per lesson slot (73 files, 13,140 lesson slots) | yes |
| **L3 — bundle** | `public/curriculum/*.json` | what the portal actually serves: per-grade indexes, per-grade/per-subject files, per-subject **schedules**, the question bank, and `_BUILD_REPORT.json` | yes, deliberately (it is the offline dataset) |

Plus: `data/questions/` (author questions — hand-written `B{2..9}.json` and machine-generated
`B{2..9}.generated.json`), `data/sources/` (the 27 NaCCA source PDFs), `data/audit/`,
`data/reference/` (a second, partly divergent copy; never a headline total), `data/books/`.

The **golden rule**: `public/curriculum/` is a *build output* that is committed on purpose, so it
must always match `data/`. That is what `make check`'s "bundle does not match the data it is built
from" step enforces.

### 8.2 The commands that matter

| Goal | Command |
|---|---|
| Rebuild the bundle after a data change | `make build-curriculum` (or `PYTHONPATH=. python scripts/build_app_curriculum.py`) |
| Regenerate the audit + headline numbers | `make audit` (writes `data/inventory.json`) |
| Validate the served bundle | `make validate-curriculum` |
| Validate + copy the question bank | `make questions` (validate, report only) / `make build-questions` (writes) |
| Regenerate the generated questions | `python3 scripts/generate_question_bank.py --apply` |
| Generate Word schemes / records of work | `make generate-schemes` / `make generate-records` (needs `python-docx`) |
| Book skeletons and the rollout | `make book-skeleton SUBJECT=mathematics GRADE=B1`, `make books-rollout`, `make books-generate`, `make books-publish SUBJECT=… GRADE=…` |
| The whole pre-deploy gate | `make check` |

On Windows without `make`, run the underlying commands directly, e.g.
`$env:PYTHONPATH="."; python scripts/build_app_curriculum.py`. Every `make` target is a one-liner
you can read in the `Makefile`.

### 8.3 Adding a question by hand

1. Open `data/questions/mathematics/B4.json` (the hand-written file for that year; the generator
   never touches it).
2. Add an item with a unique id, e.g.:

```json
{
  "id": "B4.1.2.3.4-authored-1",
  "indicatorCode": "B4.1.2.3.4",
  "type": "short",
  "prompt": "Find 35% of GH₵240.",
  "answer": "GH₵84",
  "marks": 2,
  "source": "authored"
}
```

3. Rules the merge enforces (`scripts/build_question_bank.py`): ids must be unique across authored
   **and** generated items; an `mcq` needs at least two distinct options *including* the answer;
   every non-mcq needs a non-empty answer; marks must be a positive integer; the indicator code
   must exist in the served curriculum.
4. `make build-questions`, then `make check`, then commit `public/curriculum/questions/*` and
   `data/inventory.json` along with your data change.

Use `type: "essay"` for long-answer items — the exam builder's Section C is composed from those,
so a year with no essays has no Section C.

### 8.4 The generated half, and its two traps

`scripts/generate_question_bank.py` holds 124 rules; each states its numbers in the prompt and
computes the answer, and a rule only fires where the *lower-cased* indicator description matches
its pattern.

- **Patterns must be lowercase.** `indicator_text()` lower-cases the description, so a rule written
  with a capital letter never fires. (A `Kilogram` branch was dead for months because of this.)
- **Watch for substrings.** `cedi` matches inside "pre**cedi**ng", `mode` inside "**Mode**l". Every
  word-naming pattern needs `\b`.

After changing a rule, run `python3 scripts/generate_question_bank.py --verify` (part of
`make check`): it fails if the committed generated files differ from what the rules produce. For
arithmetic changes, re-run an answer-verification pass — recomputing answers from the prompt text
is how the fraction operand-order bug was found.

### 8.5 Schedules: the term data the planners and the exam builder read

`public/curriculum/schedules/<grade>-<subject>.json` is the only thing in the repo that knows
which indicators a **term** teaches. `useSchedules` reads one file per pick (about 0.5 MB), which
is why planners do not freeze the browser.

They are **regenerated from `data/lessons/`, never hand-edited** — `make build-curriculum` writes
them. If a term's scope looks wrong, the fix is in the lesson data, not in the schedule file.

**Done when:** `make check` exits 0 after your data change, and the bundle diff in git contains
your change and nothing else.

### 8.6 The Python pipeline map

All of these are report-only by default; they write only when told to, or when they are explicitly
build steps:

| Script | Purpose |
|---|---|
| `scripts/build_inventory.py` | derives every headline number from `data/` into `data/inventory.json` |
| `scripts/audit/audit_a_databases.py`, `audit_b_pdf_crosscheck.py`, `audit_c_b*.py` | cross-check the extracted databases against the source PDFs, per grade band |
| `scripts/build_app_curriculum.py` | builds the whole served bundle (`public/curriculum/`) |
| `scripts/validate_app_curriculum.py` | re-checks the committed bundle (runs inside `make check`) |
| `scripts/generate_question_bank.py` / `build_question_bank.py` | generate and merge/validate the question bank |
| `scripts/generate_schemes.py`, `generate_records_of_work.py` | Word documents for teachers (python-docx) |
| `scripts/build_books_rollout.py`, `package_books.py`, `seed/build_book_skeleton.py` | the book product |
| `scripts/verify_deploy.py`, `verify_deploy.mjs` | the deploy pre-flight |
| `scripts/check_scripts.py` | fails if a script cannot import its own compatibility shim |
| `scripts/fix_*.py`, `promote_*.py` | one-shot data repairs, documented as much as used |

The `data/sources/` PDFs are the ground truth for provenance. `docs/curriculum-data.md` records
which subject-grades have been cross-checked against them and which are extraction-only — do not
"fix" a number without checking the PDF.

---

## Part 9 — The codebase, so you can change it

### 9.1 How a page works (the shape of every screen)

A typical portal page is three things: a hook that reads Firestore, a `DataError` for failures,
and a form or list for the happy path. This is the whole pattern:

```jsx
import { useAuth } from '../context/AuthContext'
import { usePagedCollection } from '../hooks/useCollection'
import DataError from '../components/DataError'
import { SkeletonList } from '../components/Skeleton'

export default function Forecasts() {
  const { user } = useAuth()
  const { rows, loading, error, hasMore, loadMore } = usePagedCollection('weekly_forecasts', {
    filters: [['authorId', '==', user.uid]],   // the rule asks for the owner, so the query must too
  })

  if (loading) return <SkeletonList rows={4} />
  if (error) return <DataError what="your schemes" error={error} />
  return <ul>{rows.map((row) => <li key={row.id}>{row.title}</li>)}</ul>
}
```

Three rules encoded in that snippet, each of which is a bug when broken:

1. **The query must be provable against the read rule.** Firestore rejects a whole *list* query if
   the rules cannot be proven for every document it might return. `where('authorId','==',uid)` is
   what makes the list legal for an ordinary member. An un-filtered list of a
   visibility-gated collection is `permission-denied` — for members only, which is why an admin
   testing the app sees nothing wrong.
2. **`DataError`, not an empty state, for failures.** A read error must never look like "nothing
   here yet".
3. **Ordering is opt-in.** `usePagedCollection` always orders server-side and pages with a cursor,
   so "load more" and "that's everything" are honest.

### 9.2 The hooks you will use

| Hook | Reads | Notes |
|---|---|---|
| `useCollection(name, {filters, sort, max, ordered})` | any collection, live via `onSnapshot` | `ordered: true` means the *server* sorts — and on a filtered query that needs a composite index |
| `usePagedCollection(name, {filters, sort, pageSize})` | the same, paged | returns `hasMore`, `loadMore`, `moreError`; used by Members, Notes, Plans, Question bank, Library |
| `useDoc(name, id)` | one document, live | `row` is `null` when it does not exist |
| `useCurriculum(grade)` | `public/curriculum/…` (static) | indicators for a grade, cached by the service worker |
| `useSchedules(grade, subjectId)` | one schedule file | what a **term** teaches — used by planners and the exam builder |
| `useGradeSchedules(grade)` | every schedule for a grade | pages them in so the calendar does not freeze |
| `useLibrarySave()` | — | the "Save to library" behaviour, including the no-Storage case |
| `useWisdom()` | `/quotes/*.json` | quote of the day |

### 9.3 Where logic lives (`src/lib/`)

Pure modules, all unit-tested without Firebase — this is where you put anything you want to be
able to reason about:

| Module | Responsibility |
|---|---|
| `examPaper.js` | `SECTION_PLAN`, `sectionBudgets()`, `composePaper()`, `termScope()`, `coverageOf()`, `groupMissing()` — the exam builder's whole brain |
| `questionPaper.js` | renders a composed paper to PDF (student + teacher copies) |
| `starterBank.js` | reads the served bundle and imports questions into Firestore |
| `lessonPlanDocx/Pdf.js`, `schemeDocx/Pdf.js`, `noteDocx/Pdf.js` | the exporters |
| `docxShared.js`, `htmlBlocks.js` | shared Word helpers and rich-text → Word blocks |
| `quizPptx.js`, `lessonSlidesPptx.js` | PowerPoint generation |
| `generatedDocs.js` | the document library: upload, list, open, delete, **and the no-Storage handling** |
| `academicCalendar.js` | the Ghana academic calendar (pure/static) |
| `week.js`, `grades.js`, `subjectThemes.js`, `teachingModels.js`, `lessonTemplate.js`, `docIds.js` | small pure helpers |
| `authError.js`, `dataError.js`, `profile.js` | the wording and shape of the first screens a new deployment meets |

### 9.4 Conventions that will bite you if you ignore them

- **"Adjust state during render", not in an effect.** React's `react-hooks/set-state-in-effect`
  rule is an *error* here (the React Compiler is enabled). When state must reset because a
  derived value changed, do it with a "last seen" guard during render.
- **Effects are for subscriptions only** — `onSnapshot`, listeners — and must return their
  unsubscribe. Guard a `getDoc().then()` with an `active` flag.
- **Every Firestore write stamps `authorId: user.uid` and `serverTimestamp()`.**
- **`import.meta.env` is read at build time.** A new variable means Vercel *and* `.env.local`.
- **Keep the rules and the client in step.** `src/firestoreRules.test.js` scans the client for
  `collection(db, '…')` names and fails if one has no rule; `src/firestoreIndexes.test.js` derives
  every index the app's queries need. Adding a collection means editing `firestore.rules` in the
  same change.
- **`src/sidebarRoutes.test.js`** fails if a sidebar link points at a route the router does not
  declare. Add the link and the route together.

---

## Part 10 — Build a feature end to end (worked example)

The exam paper builder (`/portal/questions/exam`) is the best template in this codebase: it
touches data, pure logic, UI, exports and rules. Here is its anatomy, in the order it was built.

**1. The data question.** Where do questions come from? A static bundle
(`public/curriculum/questions/…`), imported into Firestore via the starter bank, plus questions
members author. Both end up in the `questions` collection, so the feature reads one source.

**2. The pure core, first.** `src/lib/examPaper.js`:

- `SECTION_PLAN` — the three sections and their share of the marks (A 40%, B 35%, C 25%).
- `sectionBudgets()` — pre-rounds those shares so they sum to the target *exactly* (rounding them
  one by one is how a 50-mark paper once came out at 51).
- `composePaper(pool, { targetMarks, sectionIds })` — fills each section from its share of the
  pool, then **rolls the marks a section cannot spend into the sections that can still print**
  (a year whose pool has no long-answer items is a full-length paper of Sections A and B, not a
  short one). It never exceeds `targetMarks`, it names any section it could not use
  (`kind: 'too-long' | 'no-candidates'`), and it reports the shortfall only when the pool itself
  runs out.
- `termScope()` / `filterByIndicators()` / `coverageOf()` / `groupMissing()` — the honest
  "Term 2 schedules 56 indicators; the pool asks about 56 (100%)" line.

Written and tested **before** any UI: `src/lib/examPaper.test.js` (23 tests) pins the arithmetic,
so the page can stay thin.

**3. The page.** `src/pages/ExamBuilder.jsx` holds the pickers (grade, subject, term, target
marks), calls the pure functions, renders the preview, and offers the exports. It contains no
paper logic — which is why the preview can never disagree with the PDF.

**4. The exports.** `src/lib/questionPaper.js` renders the composed paper twice: a student copy
and a teacher copy with the marking scheme, both via jsPDF.

**5. The safety net.** `src/sidebarRoutes.test.js` asserts the route exists and that the page
still calls `buildQuestionPaper`; the starter bank has its own test; the `questions` collection
already had rules and an index.

**6. The evidence.** The feature is described in `docs/features.md`, its subtle rules in
`docs/gotchas.md`, and its verification steps in `docs/verification.md` (19a–19e).

Copy that order — **data → pure logic + tests → page → exports → guards → docs** — for any feature
you add. It is the reason this codebase has 421 tests and no browser tests: everything worth
testing lives outside React.

---

## Part 11 — Documents, exports and the font trap

Everything a teacher can take away is generated **in the browser**:

| Export | Module | Format |
|---|---|---|
| Lesson plan | `lessonPlanDocx.js` / `lessonPlanPdf.js` | Word / PDF |
| Scheme of learning | `schemeDocx.js` / `schemePdf.js` | Word / PDF |
| Study note | `noteDocx.js` / `notePdf.js` | Word / PDF |
| Exam paper (student + teacher) | `questionPaper.js` | PDF |
| Quiz slideshow | `quizPptx.js` | PPTX |
| Lesson slides | `lessonSlidesPptx.js` | PPTX |

The trap, and it is a silent one: **jsPDF can only render WinAnsi characters**. A `√`, `π`, `≥`,
`GH₵` or `Ɛ` in a question produces `\u0000`-pair garbage in the PDF — no error, just a corrupted
paper. Characters like `° ² × ÷ ¢ ½ ³` are fine. The rule in this codebase is therefore: **word
the mathematical symbols** (say "the square root of", "pi", "at least"), and keep every prompt,
answer and option inside WinAnsi. Two guards enforce it:

- `src/lib/starterBank.test.js` — "keeps every question printable by the exam paper font", over
  every served question;
- the authored-question pipeline rejects any code point above U+00FF that jsPDF cannot print.

If you add an export, add it to this list and give it a guard test in the same change.

### Saving to the library (optional feature)

`SaveToLibrary` (`src/components/SaveToLibrary.jsx`) appears on every page that produces a file.
It uploads the blob to Cloud Storage under `generated/{uid}/…`, writes a record to
`generated_documents`, and lists them at `/portal/library`. The rules make the folder private.
Without a Storage bucket the button is replaced by one line explaining that, and the export still
downloads — that path is deliberate and tested (`generatedDocs.test.js`).

---

## Part 12 — The security model in one page

Two files, one idea: **the client is untrusted; the rules are the truth.** Between them they
cover 21 collections (`users`, `articles`, `vacancies`, `notes`, `lesson_plans`,
`weekly_forecasts`, `questions`, `lesson_slides`, `generated_documents`, `posts`, `progress`,
`quote_likes`, … and a tail of deliberately inert ones reserved for later phases).

**Roles and status** (`users/{uid}`):

| Field | Values | Meaning |
|---|---|---|
| `status` | `pending` (default at sign-up) · `approved` · `suspended` | only an **admin** may change it |
| `role` | `member` (default) · `admin` | only an admin may change it |

Sign-up may write its own document **only** with `status: 'pending'` and `role: 'member'` — the
single most important line in `firestore.rules`, because a client that could write its own
`approved` would walk past every other rule.

**Who can read what:**

- **Anyone** may read published articles and vacancies (the public pages), which is why those two
  queries carry a matching `where(...)`.
- **Any approved member** may read the curriculum (it is static JSON anyway), the shared content
  libraries, and their own private drafts.
- **Visibility-gated collections** (`notes`, `lesson_plans`, `weekly_forecasts`) are readable when
  the document is the caller's own, or `visibility` is `members`/`public`. This is why those pages
  offer two tabs (Mine / Shared) and why **an un-filtered list of them is denied** — the reason
  the client has exactly two provable queries per collection.
- **Admins** may additionally read everything for support, and manage members.
- **Storage** (if enabled): a member may read, write, list and delete only their own
  `generated/{uid}/…`, capped at 8 MiB per file; admins may read.

**Indexes** are part of this story: a rule can be right and a page still be empty, because a
filtered + ordered query needs a composite index. `firestore.indexes.json` lists 19, and
`src/firestoreIndexes.test.js` derives them from the app's queries so a new one cannot be
forgotten.

Read `docs/security.md` for the threat model and `docs/gotchas.md` for the list of ways this has
gone wrong in practice — both are short and worth your time before you touch the rules.

---

## Part 13 — Offline behaviour (the PWA)

- **What is cached**: the app shell and the 39 MB curriculum bundle, under a cache named
  `beacon-<bundleHash>`. The hash comes from `public/curriculum/_BUILD_REPORT.json`, so a
  curriculum rebuild renames the cache and returning browsers drop the old one — no "clear site
  data" advice needed.
- **Strategy**: navigations are network-first; static assets are stale-while-revalidate.
- **Firestore** is offline-capable on its own (`persistentLocalCache` in `src/firebase.js`): reads
  come from IndexedDB, writes queue and sync on reconnect.
- **Questions are deliberately excluded from the hash** — they refresh by
  stale-while-revalidate, so adding questions does not invalidate the whole cache.
- **You can only test this in `yarn preview`.** The dev server has no service worker. Use
  DevTools → Application → Service Workers for the cache name, and Network → Offline for the
  behaviour.

---

## Part 14 — Tests and CI

| Suite | Command | Covers |
|---|---|---|
| Unit + contract | `yarn test` (421 tests, 25 files) | pure logic (`examPaper`, `generatedDocs`, `profile`, `week`, …), the rules *files* as text (`firestoreRules.test.js`, `storageRules.test.js`), the bundle's integrity (`curriculumBundle.test.js`), the sidebar/router contract, the index contract, the deploy-script contract, the WinAnsi guard |
| Rules emulator | `yarn test:rules` (95 checks: 81 Firestore + 14 Storage) | real permission decisions: a pending member refused, an un-filtered list denied, a like unable to inflate its tally, uploads capped and owner-only. Needs **Java 21** |
| The gate | `make check` | `questions lint test check-scripts validate-curriculum inventory bundle-size bundle-check bundle-hash` + `yarn build` |
| CI | `.github/workflows/ci.yml` | three jobs: **Lint, test, build** · **Firestore rules (emulator)** · **Curriculum data audit** (plus Vercel's own preview-comment check run) |

CI runs on every push to any branch. From the command line you can read its verdict without the
web UI:

```powershell
gh api /repos/beaconeducationalconsult-gh/beacon-consult/commits/<sha>/check-runs `
  --jq '.check_runs[] | "\(.name): \(.status)/\(.conclusion)"'
```

If a job fails, `gh run view --log` is often blocked; use the check-run annotations instead:
`… /check-runs/<id>/annotations`.

**Writing a test**: put it next to the module (`src/lib/foo.test.js`). If it needs Firebase, mock
the module (`vi.mock('../firebase', …)`) as `generatedDocs.test.js` does; if it needs a real
Firestore, it belongs in `tests/rules/` and must run against the emulator.

---

## Part 15 — Debugging: every failure this project has actually had

Each of these cost real time. They are ordered roughly by how likely you are to meet them.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | Blank page, nothing in the UI | A missing Firebase config used to throw during module evaluation | Fixed: `main.jsx` renders `SetupNotice`. If you see a blank page, check the browser console for a *new* cause |
| 2 | Every list empty, console says `permission-denied` | A read rule that inspects document fields breaks **list** queries — Firestore needs the rule provable for every candidate document | Give the rule a document-independent branch (`isApprovedOrAdmin()`), or make the query carry a matching `where(...)` |
| 3 | Same, but only for ordinary members | You are testing as an admin, who passes branches members do not | Always verify as a member |
| 4 | Empty list, console says `failed-precondition` | A composite index is missing | Use the **Create the missing index** button on the error, or `firebase deploy --only firestore:indexes`. `src/firestoreIndexes.test.js` should have caught it |
| 5 | Deploy shows the setup notice; local build is fine | Vercel built without `VITE_FIREBASE_*` (vars are per environment) | Set them for Production **and** Preview, redeploy |
| 6 | `/build-info.json` returns HTML; schedules missing; old `sw.js` | Production is deploying a different branch (Vercel's Production Branch, `main` by default) | Phase 6.3 |
| 7 | Rules deploy "succeeds" but nothing changes | `.firebaserc` points at a different project than the app uses | `node scripts/verify_deploy.mjs` compares them; `firebase use <the app's project>` |
| 8 | Every library upload denied | `storage.rules` never published (or `matches()` written without a trailing `.*` — RE2 matches the *whole* string) | Publish `storage.rules`; end patterns with `.*` |
| 9 | `auth/operation-not-allowed` on sign-up | Email/Password provider not enabled | Phase 2.3 |
| 10 | `auth/unauthorized-domain` | The deployed domain is not in Authorized Domains | Phase 2.3 |
| 11 | Signed in but the portal says "Awaiting approval" with no name/school | Sign-up ran before the rules were published: the Auth account exists, the `users/{uid}` row does not | The portal offers **"Finish setting up your account"**; publish the rules to stop it recurring |
| 12 | A question renders as `\u0000` pairs in a PDF | A character jsPDF cannot encode in WinAnsi | Word the symbol; the guards are in `starterBank.test.js` |
| 13 | "All six values missing" although you can see them in `.env.local` | PowerShell wrote the file as UTF-16 | Write it as UTF-8 (Phase 3.1) |
| 14 | `cat`/`ls` fails inside the build, or `bundleHash` is `null` on Windows | A build plugin used a Unix shell command | Use Node APIs (`node:fs`) in `vite.config.js`; there is a test forbidding shell commands there |
| 15 | `yarn` refuses: *"packageManager: yarn@4.9.4, current version 1.22.22"* | Global Yarn 1, Corepack not enabled | `corepack enable`, reopen the terminal, or use `corepack yarn …` |
| 16 | `firebase: The system cannot find the path specified` | A stale global shim | Use `npx --yes firebase-tools@15.30.2 …` |
| 17 | Rules tests fail on your machine, pass in CI | No JVM | `yarn test:rules` needs Java 21; CI has its own job for it |
| 18 | `make check` exits 2 with a diff under `public/curriculum/` | The committed bundle is stale after a data change | `make build-curriculum`, then commit the bundle **and** `data/inventory.json` |
| 19 | Windows checkout shows every rules test failing | CRLF line endings vs an LF parser | Fixed: the rules tests normalize on read. If you write a new `;\n` parser, normalize too |
| 20 | A generated question has the wrong answer | A generator rule computed it wrongly (e.g. a fraction's operands swapped) | Re-run the answer-verification pass: recompute from the prompt text, then add a regression case |
| 21 | `firebase deploy` ends with `HTTP Error: 400, this index is not necessary` | `firestore.indexes.json` contains an entry with a **single field** — Firestore creates single-field indexes itself | Delete that entry (an unfiltered `orderBy` needs no entry; a filtered + ordered query needs two fields or more) and re-run the deploy — it is idempotent. `src/firestoreIndexes.test.js` fails on one now |
| 22 | `[W] Unused function: …` on every deploy | A rule helper nothing calls | Remove it, or use it. An always-present warning hides the next, real one; `src/firestoreRules.test.js` now fails on an uncalled function |
| 23 | The live site shows **Firebase configuration is missing** instead of the portal | The **build** had no `VITE_FIREBASE_*` values — Vite inlines them at build time, so a `.env.local` on your laptop is not part of the deploy, and a value scoped to Preview only is not part of a production build either | `GET <domain>/build-info.json` names the missing values (`firebaseConfigured`, `missingEnv`). Add them in Vercel → Settings → Environment Variables for **Production *and* Preview**, then *Deployments → Redeploy* — a variable change does not rebuild by itself |
| 24 | …and it is still there after you set them | The variables are on a different Vercel project, or scoped to Preview/Development only, or you redeployed a *preview* deployment (a promoted preview keeps the environment it was built with) | The values are committed in `src/firebaseConfig.js` and `src/firebase.js` falls back to them, so this should not be reachable — if it is, that file is empty or has a typo, and `/build-info.json` says `configSource` |

The full, longer list — with the reasoning — is `docs/gotchas.md`. It is the most valuable file in
the repository after this one.

---

## Part 16 — Command reference

**Daily development**

```powershell
yarn install              # dependencies (after a pull that touched package.json/yarn.lock)
yarn dev                  # dev server           → http://localhost:5199
yarn build                # production build     → dist/ (+ build-info.json)
yarn preview              # serve the build      → http://localhost:4173  (only place the PWA exists)
yarn lint                 # ESLint — must be clean
yarn test                 # unit + contract tests
yarn test:rules           # permission matrix against the emulator (Java 21)
yarn test:watch           # tests on save
```

**The gate and the data**

```powershell
make check                # what CI runs: questions, lint, tests, scripts, bundle validation, inventory, build
make build-curriculum     # rebuild public/curriculum/ from data/      (then commit!)
make audit                # regenerate data/inventory.json and list every dataset gap
make questions            # validate the question bank (report only)
make build-questions      # validate and write it
make generate-schemes     # Word schemes into dist/                   (needs python-docx)
make generate-records     # Word records of work into dist/
```

**Firebase and deploys**

```powershell
npx --yes firebase-tools@15.30.2 login
npx --yes firebase-tools@15.30.2 use <project-id>
npx --yes firebase-tools@15.30.2 deploy --only firestore:rules,firestore:indexes
npx --yes firebase-tools@15.30.2 deploy --only storage         # only if Storage is enabled

node scripts/verify_deploy.mjs                                  # local half only
node scripts/verify_deploy.mjs -Url https://your-deploy.vercel.app/
.\scripts\deploy_check.ps1 -Url https://your-deploy.vercel.app   # the same, from PowerShell
```

**Git, for this repository**

```powershell
git status --short            # what you changed
git pull --ff-only            # update; refuses rather than surprising you
git add -A; git commit -m "…"
git push origin arena/01a0af88-beacon-consult
```

---

## Part 17 — Where everything is documented

| Read this | For |
|---|---|
| `SKILL.md` (this file) | building the project from nothing, and the map of everything else |
| `README.md` | the short version: what it is, quick start, command table |
| `docs/features.md` | every feature, page by page, with its route and its rules |
| `docs/architecture.md` | how the app is put together and why |
| `docs/data-model.md` | every Firestore collection and field |
| `docs/security.md` | the threat model and the role matrix |
| `docs/gotchas.md` | **the 20+ failures that really happened**, and how to avoid them |
| `docs/curriculum-data.md` | the three data layers, the counts, and what is audited vs extraction-only |
| `docs/build-deploy.md` | Firebase console setup, environment variables, Vercel, the update workflow |
| `docs/verification.md` | the deploy checklist and the symptom → cause table |
| `docs/pwa-offline.md` | the service worker and offline behaviour |
| `docs/conventions.md` | the coding conventions the linter enforces |
| `docs/playbooks.md` | procedures for recurring tasks |
| `docs/TODO.md` | what is done, what is open, and what was decided (the project's memory) |
| `docs/project-state.md` | the five surfaces (GitHub, Firebase, Vercel, your machine, the sandbox) + your browser, and the 60-second triage |
| `docs/code-bible.md`, `docs/project-blueprint.md` | the original design documents |
| `docs/NACCA_QUESTION_BANK.yaml` | the question-bank specification |

`docs/git-dictionary.md` and `docs/project.md` are the owner's files — read them, but do not edit
them. (`docs/project-state.md` is the map of the five places the project lives, and the triage to
run when something looks wrong.)

---

## Part 18 — Phases at a glance (print this)

```
Phase 0   Understand: React PWA + Firebase backend + Python data pipeline. No server to run.
Phase 1   Tools: Git, Node 22, corepack enable (Yarn 4), Python 3.11+.
          git clone --branch arena/01a0af88-beacon-consult …
          yarn install && yarn dev → 5199 → "not configured yet" is correct.
Phase 2   Firebase console: create project → Firestore (Native, Production mode) →
          Authentication (Email/Password ON, add your domain) → register Web app (copy 6 values)
          → [optional: Storage, needs Blaze] → .firebaserc = your project id.
Phase 3   .env.local with the six VITE_FIREBASE_* values (UTF-8! no quotes!) → restart dev.
          node scripts/verify_deploy.mjs -SkipBuild → config complete, projects match.
Phase 4   Sign up in the app → console: users/{uid} → role: "admin", status: "approved" → reload.
          (Rules before sign-up, or use "Finish setting up your account".)
Phase 5   npx firebase-tools login → use <project> → deploy --only firestore:rules,firestore:indexes
          [→ deploy --only storage if enabled].  yarn test:rules.
Phase 6   Vercel: env vars (Production + Preview) → Production Branch = arena branch → Redeploy.
Phase 7   node scripts/verify_deploy.mjs -Url <deploy>  (all green)
          docs/verification.md section 2, as an ordinary member.
Phase 8   Data: make build-curriculum → commit bundle + inventory; questions via data/questions.
```

**Where the value is, if you are deciding what to do next:** the curriculum dataset and the
question bank (Phases 8) are the parts nobody else has; the portal around them is what makes them
usable in a classroom with intermittent internet. Whatever you build, keep the offline path
working — a teacher with no connection is the user this was designed for.
