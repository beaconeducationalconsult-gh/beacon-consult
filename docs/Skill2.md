# Skill2.md — Building **Beacon Consult** from zero

*A complete, start-to-finish guide for someone who has never seen this project. Every command
here was run against this repository; every error in Part 15 is one this project actually hit.*

> **This is a corrected revision of `SKILL.md`.** It supersedes the older copy and fixes a set of
> statements that became untrue when commit `a98c94b` ("Commit the Firebase config as source")
> changed how the app gets its Firebase config. The single most important correction:
>
> **A fresh clone no longer shows a "not configured" setup notice.** The six Firebase values are
> now committed in `src/firebaseConfig.js`, and `src/firebase.js` falls back to them whenever the
> environment does not supply a value. So `yarn dev` on a brand-new checkout boots the **full app,
> connected to the live production project `beacon-edu-consult-proj`** — not a harmless placeholder.
> Phase 1 now tells you how to run the toolchain *without* writing to production. See
> [Corrections in this revision](#corrections-in-this-revision) at the end for the full list.

---

## How to read this

The guide is written in **phases**. Each phase ends with a *Done when* checklist — if the check
fails, do not continue to the next phase; the next one assumes the last one worked.

| Phase | You will | Time | Needs |
|---|---|---|---|
| **0** | Understand what you are building | 15 min | nothing |
| **1** | Run the app on your machine — safely, without touching production | 30 min | Node, Git, Yarn |
| **2** | Create the Firebase project (the "backend") | 30 min | a Google account |
| **3** | Connect the app to *your* project locally | 15 min | Phase 2 |
| **4** | Become the first administrator, and sign in | 20 min | Phase 3 |
| **5** | Publish the security rules and indexes | 20 min | Phase 4, Node |
| **6** | Put it on the internet (Vercel) | 30 min | Phase 5 |
| **7** | Verify the deploy end to end | 45 min | Phase 6 |
| **8** | Work on the data (curriculum, questions, books) | open-ended | Python |

Three rules of thumb before you start:

1. **Never mix package managers.** This project is Yarn 4. `npm install` here creates a second,
   conflicting lockfile and a broken `node_modules`. Use `yarn` for JavaScript, `pip` for Python.
2. **A fresh clone points at production.** The committed Firebase config means `yarn dev` is live
   against `beacon-edu-consult-proj` until you override it. Read Phase 1.0 before you sign up or
   write anything.
3. **The order in Phases 4–5 matters** (rules before sign-up). Where it does, the guide says why,
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
   scripts under `scripts/` and `seed/`. They are the sellable artefacts; they are not part of the
   web app.

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

### How the app gets its Firebase config (read this once, thank yourself later)

There are **two** sources of the six `VITE_FIREBASE_*` values, and a fixed rule for choosing
between them (`src/lib/firebaseConfigSource.js`):

1. **The build environment** — `.env.local` on your machine, or Vercel's environment variables.
2. **The committed file** — `src/firebaseConfig.js`, which holds the real production values and
   ships in the repository.

The rule, per value: **a non-blank environment value wins; anything blank or absent falls back to
the committed file.** A variable that exists in the environment but is *empty* counts as absent
(and is named in the build log, because an empty Vercel variable once silently blanked a good
value). `dist/build-info.json` records which side a build used, as `configSource`
(`env` / `committed` / `mixed`).

Two consequences worth internalising now:

- **A build always has a working config**, so the "green build, setup notice" failure is gone —
  but a fresh clone therefore talks to **production** by default.
- **To point the app at a different project** (yours, or a throwaway), supply the six values in
  the environment; you do not edit the committed file. Phase 1.0 and Phase 3 both rely on this.

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

## Phase 1 — Run it on your machine (safely)

### 1.0 First: decide what you want `yarn dev` to talk to

Because the config is committed, a fresh clone is **already configured** — against the live
production project. Before you run anything that writes (sign-up, save a note, import questions),
pick one of these:

| Goal | Do this | Result |
|---|---|---|
| **Just prove the toolchain** (compile, mount, tests) | Run `yarn install`, `yarn test`, `yarn lint`, `yarn build`. Browse `/` but **do not sign up**. | No writes to production. The public pages and the curriculum browser are read-only and safe. |
| **See the setup notice** (the old "not configured" screen) | Temporarily blank the committed config *and* have no `.env.local`: in `src/firebaseConfig.js` set the six values to `''` (do not commit), then `yarn dev`. | `firebaseConfigured` is false → `main.jsx` renders `SetupNotice`. Revert the file afterwards. |
| **Develop against your own project** (recommended for anything beyond reading) | Do Phase 2, then put your six values in `.env.local` (Phase 3). Env wins over the committed file. | Your dev server reads/writes *your* Firebase project, never production. |

> **Why this box exists.** The previous revision of this guide told you a fresh clone "will show a
> setup notice" and that you could "complete Phase 1 with no Firebase project at all." That was true
> before the config was committed; it is **false now**. Following the old text signs a newcomer
> straight into production Firestore. Signing up creates a real `users/{uid}` document (pending),
> and any content you author is real. Read-only browsing is harmless; writes are not.

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

Open <http://localhost:5199>. **You will see the working portal, not a setup notice** — the
committed config connects you to `beacon-edu-consult-proj`. That is expected. Confirm the
toolchain by the three things that do not write:

- Vite compiled and React mounted with no red error on screen;
- `yarn test` passes (421 tests);
- `yarn lint` is clean.

If you *want* the setup notice (to see what an unconfigured build looks like), follow the middle
row of the Phase 1.0 table. The notice only appears when **both** the environment and
`src/firebaseConfig.js` are blank — `main.jsx:19` renders `SetupNotice` solely when
`firebaseConfigured` is false.

Commands you will use constantly:

```powershell
yarn build            # production build into dist/  (also writes dist/build-info.json)
yarn preview          # serves dist/ on http://localhost:4173
yarn lint             # ESLint, including the React Compiler rules — must stay clean
yarn test             # the unit + contract suite (421 tests, 25 files, no browser, no Python)
```

**Service workers only exist in `yarn preview`**, never in `yarn dev`. Anything offline-related
must be tested against the preview server. That is why both ports are pinned: dev `5199`,
preview `4173` (they are declared in `vite.config.js` and `.claude/launch.json`).

### 1.4 Know your way around the tree

```
beacon-consult/
├── src/                  the portal (React) — the app you deploy
│   ├── main.jsx          entry: renders SetupNotice ONLY when no config resolves (env + committed both blank)
│   ├── App.jsx           every route, and the portal's approval gate
│   ├── firebase.js       initialises Firebase: env value wins, else falls back to the committed config
│   ├── firebaseConfig.js the six committed production values (the fallback every build can read)
│   ├── pages/            one file per screen (42 of them)
│   ├── components/       shared UI — 18 files (Sidebar, DataError, PendingApproval, SaveToLibrary, SetupNotice …)
│   ├── hooks/            useCollection / usePagedCollection / useCurriculum / useSchedules / useLibrarySave
│   ├── context/          AuthContext (who am I, approved?) and ToastContext
│   └── lib/              pure logic — 27 modules: exam papers, exports, calendar, starter bank,
│                         profile, firebaseConfigSource (the env-vs-committed rule), setupGuidance …
├── public/               served as-is: curriculum bundle, quotes, sw.js, manifest
│   └── curriculum/       ~39 MB of static JSON — the offline dataset the app reads
├── data/                 the SOURCE data (curriculum DBs, lessons, questions, audits)
├── scripts/              Python: audit the data, build the bundle, generate books, verify a deploy
├── seed/                 Python: book skeletons
├── legacy/               the retired NCOS app — reference only, nothing imports it
├── docs/                 the long-form documentation (doc map in Part 17)
├── firestore.rules       who may read/write Firestore — you publish this
├── storage.rules         the same for uploaded documents (only if you enable Storage)
├── firestore.indexes.json  the 18 composite indexes the app's queries need
├── firebase.json         tells the Firebase CLI where those three files are
├── .firebaserc           which Firebase project the CLI deploys to
├── .env.example          the six VITE_FIREBASE_* names (all optional — see Phase 0)
├── vercel.json           SPA rewrite + cache headers for the deploy
├── vite.config.js        build config + the beacon-build-info plugin (writes dist/build-info.json)
├── Makefile              the task runner (make check, make build-curriculum, …)
├── SKILL.md              the previous revision of this guide
└── Skill2.md             this file
```

**Done when:** `yarn test` passes (421), `yarn lint` is clean, and `yarn dev` serves the app at
<http://localhost:5199> — and you have decided, per Phase 1.0, whether that dev server is allowed
to write to production.

---

## Phase 2 — Create the Firebase project (the backend)

Firebase is the whole backend: accounts, database, and (optionally) file storage. Nothing here is
done by Vercel or by the build; a deploy cannot create these for you, and each missing piece has
its own error message later.

Open <https://console.firebase.google.com> and do these in order. **Steps 2.1–2.4 are console
work; 2.5 is the only one that needs the command line.**

> Skip this whole phase if you only intend to develop against the existing production project.
> You need your own project the moment you want to write data without touching production, or you
> are standing up a second school/deployment.

### 2.1 Create the project

**Add project** → name it (the display name can be anything: `beacon-edu-consult`) → Analytics is
optional (this app does not use it) → Create.

Note the **project id** — the immutable one in the URL and under ⚙︎ *Project settings*, like
`beacon-edu-consult-proj`. It is *public* (it ships in the browser bundle) but it must be **the
same** in the places that matter, or you will publish your rules to a project your app never talks
to:

1. the app's effective `projectId` — from `.env.local`'s `VITE_FIREBASE_PROJECT_ID`, or, if that is
   blank, from `src/firebaseConfig.js` (Phase 0);
2. `.firebaserc` in this repo (what `make deploy-rules` follows);
3. the console you are looking at.

`src/firebaseConfig.test.js` enforces parity between the committed config and `.firebaserc`, so if
you change one for a new project, change the other in the same commit.

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

Keep this list tight — no wildcards. Because the Firebase config is public (and now committed),
**the Authorized Domains list plus `firestore.rules` are the only real barriers**; an open domain
list weakens both.

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

Those six values are what you put in `.env.local` (Phase 3) to point the app at *your* project.
They are **identifiers, not secrets**: they are published in the JavaScript bundle by design, which
is why the security lives in the rules and in the Authorized Domains list, never in the key. That
is also why committing them in `src/firebaseConfig.js` is acceptable — but see the caution below.

> **Committing config is a deliberate trade-off, not an accident.** The values are public in the
> bundle either way; putting them in source removes two silent deploy failures (a BOM eating the
> first line of a `.env` file, and a blank environment variable shadowing a good value). The cost:
> the production project id and API key are readable by anyone with repo access, and **rotating or
> repointing the project means editing `src/firebaseConfig.js` and re-deploying**, not just changing
> a dashboard variable. If this repository is or becomes public, treat the Firebase project as
> publicly reachable and rely entirely on the rules + Authorized Domains being correct.

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

> Two files, two tools, one project: your app's effective config (`.env.local`, gitignored, or the
> committed `src/firebaseConfig.js`) and `.firebaserc` (the CLI, committed). If they disagree,
> `make deploy-rules` publishes the rules to a project your app never reads — a *successful deploy
> to the wrong database*, which is a very expensive kind of silence. `node scripts/verify_deploy.mjs`
> (Phase 3.3) compares them and refuses to call it a pass.

**Done when:** the project exists, Firestore is created in Native mode, Email/Password is enabled,
a web app is registered (its config copied somewhere safe), and `.firebaserc` names the project.

---

## Phase 3 — Connect the app to *your* project (local)

You only need this phase if you created your own project in Phase 2 and want your dev server to
use it instead of the committed production config. If you are developing against production, skip
to Phase 4 — but re-read Phase 1.0 first.

### 3.1 Create `.env.local` (the override)

`.env.local` is gitignored: a fresh clone has none, and that is fine — the app falls back to
`src/firebaseConfig.js`. Creating `.env.local` is how you **override** the committed values with
your own project's. Copy the template and fill in the six values from Phase 2.4:

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

A non-blank value here wins over the committed file. A value you leave **empty** does *not* blank
the committed one — it is treated as absent and falls back (and the build log names it). So a
partially filled `.env.local` is safe: any key you omit comes from `src/firebaseConfig.js`.

Rules that are not obvious:

- **Keep the `VITE_` prefix.** Vite only inlines variables with it; renaming breaks the override.
- **No quotes, no spaces around `=`** (Vite tolerates quotes, but half the tools in this project
  do not).
- **Write it as UTF-8, and do not use PowerShell's `>` or `Out-File`.** Windows PowerShell writes
  those as **UTF-16**, and `Set-Content -Encoding utf8` adds a **BOM** that Vite's parser does not
  strip — either way a key silently "disappears". Use an editor, or
  `Set-Content .env.local -Encoding utf8NoBOM -Value @('VITE_FIREBASE_API_KEY=…', …)` if your
  PowerShell supports `utf8NoBOM`. (This trap is exactly why the values were moved into source.)
- **Restart `yarn dev` after editing it.** Vite reads env files at startup.

### 3.2 Start the app and sign in

```powershell
yarn dev
```

You get the public site (pointed at your project if `.env.local` is set, at production otherwise).
Sign up at `/signup` (or sign in). On a **fresh project with no rules published yet** you will land
on **"Awaiting approval"** — correct, and Phase 4 is how you get past it.

> **If sign-up reports a permission error**, that is expected at this point in the guide: a new
> database is in production mode with no rules published yet, so the *account* is created in
> Authentication but the *membership row* in Firestore is refused. The app detects this and offers
> **"Finish setting up your account"** on the portal screen; nothing is lost. Phase 5 removes the
> cause.

### 3.3 Check the local configuration like a deploy

```powershell
node scripts/verify_deploy.mjs -SkipBuild
```

This is the same pre-flight the deploy uses, stopping before the network checks. It reports:

- the branch and commit you are on (and warns about uncommitted work);
- whether all six values resolve (from `.env.local` or the committed file) — and, if not, the
  **names** of the keys it did find, never the values;
- whether `.firebaserc` pins the same project the app uses;
- what the last build in `dist/` embedded.

> **Note on the build line.** With `-SkipBuild` the script reads the *existing* `dist/build-info.json`.
> That file records the commit it was built from. If it names an older commit than `HEAD`, your local
> `dist/` is stale — harmless for Vercel (which rebuilds from source) but it means the pre-flight is
> describing an old build. Run `yarn build` before trusting that line, and always before a manual
> `dist/` deploy.

**Done when:** the app runs, you have signed up an account, and
`node scripts/verify_deploy.mjs -SkipBuild` says the config resolves completely and the projects
match.

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
| Firestore indexes | `firestore.indexes.json` (**18** composite indexes) | the *list* queries: without them Firestore answers `failed-precondition` and the page shows nothing |
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

Things you may meet here, all covered in Part 15:

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
yarn test:rules        # Firestore + Storage permission matrix: pending member refused, un-filtered list denied, upload caps…
```

The suite runs against a throwaway emulator project (`demo-beacon-rules`, see `package.json`), so
it never touches real data. The exact check count is printed when it runs (the two files are
`tests/rules/firestore.rules.test.js` and `tests/rules/storage.rules.test.js`); older revisions of
this guide quoted 95 and 97 in different places — trust the run, not the number in the doc.

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
(`vercel.json` already carries the SPA rewrite and cache headers) → Deploy. The values the app
needs are committed, so **the first deploy should come up ready to sign in with no environment
variables set at all**. If it shows the setup notice instead, `GET /build-info.json` on it says what
the build was missing and where its config came from (`configSource`).

### 6.2 Environment variables — optional now

**You do not have to set any environment variables.** The six values live in
`src/firebaseConfig.js`, and `src/firebase.js` falls back to them for anything the environment does
not supply — so a build, in Vercel or on your machine, always has a working config, and no dashboard
state can break it.

Set them only if you want to **point a deploy at a different Firebase project** without a code
change. If you do:

**Settings → Environment Variables** → add each of the six `VITE_FIREBASE_*` names and values, for
**Production *and* Preview** (Vercel keeps them per environment; setting only Production leaves
every preview deploy on the committed config). Then note:

- **Keep the `VITE_` prefix.** It is what makes Vite inline the value; removing it makes the app
  read `undefined` and fall back to the committed file (or show the notice if that is blank too).
- **A non-blank value wins; a blank one is ignored** and the committed value is used. So *delete*
  any variable you leave empty rather than committing an empty override — the build log names blank
  ones for exactly this reason.
- **Save as an ordinary Config variable, not Sensitive.** These are public by design; marking them
  Sensitive changes nothing about the bundle and breaks `vercel env pull`.
- **Changing a variable does not rebuild anything.** After adding or editing one, *Deployments →
  ⋯ → Redeploy* (or push a commit). Reloading the domain proves nothing.

If the notice is still there after you set them: they are on a *different Vercel project* (the one
whose **Domains** tab lists your address is the one that matters), or scoped to
**Preview/Development only** (read the **Environments** column), or you redeployed a **preview**
deployment (promoting a preview does not rebuild it, so it keeps the environment it was built with),
or they were added after the build began. `npx vercel env ls` prints the names and their
environments; `/build-info.json` prints `configSource` and `missingEnv`.

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
yarn build                                       # writes dist/build-info.json (from THIS commit)
node scripts/verify_deploy.mjs -SkipBuild        # config + project ids + what the build embedded
```

Build first, then verify: the pre-flight reads `dist/build-info.json`, so a stale `dist/` describes
an old commit. Confirm its `commit` field equals `git rev-parse --short HEAD` before you trust it.

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
two implementations drift apart, and now checks their six variable names against
`src/lib/firebaseConfigSource.js` — the single place the names are written down.)

It fetches the deploy and fails with an explanation for each of these:

| Check | Catches |
|---|---|
| `GET /build-info.json` → `firebaseConfigured` | A deploy built **without** any config (env blank *and* committed file blank/typo'd): green build, setup notice for every teacher |
| `build-info.json` → `configSource` | Whether the deploy used `env`, `committed`, or `mixed` values — i.e. whether an override is in play |
| `build-info.json` → `bundleHash` vs `public/curriculum/_BUILD_REPORT.json` | A deploy serving an older curriculum than the checkout |
| `build-info.json` → `projectId` vs your effective config | A deploy talking to a different Firebase project than your machine |
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

> **If you are verifying against production, use a throwaway member account and clean up after
> yourself.** Everything you create is real. Better: verify against your own project (Phase 3).

### 7.3 When a step fails

Start from the symptom; the two Firestore codes point at completely different repairs, and the app
now prints which one it is:

| Symptom | Cause | Fix |
|---|---|---|
| `permission-denied` on a whole list | Published rules are older than the build, or the account is not approved | Re-publish `firestore.rules`; check the member's `status` in `/portal/members` |
| `failed-precondition` (the page shows a **Create the missing index** button) | A composite index is missing | Click the link → Create index → wait a minute. `src/firestoreIndexes.test.js` makes this impossible for a shipped query; if it fires, a query was added without its index |
| Setup notice instead of the portal | The build resolved **no** config: environment blank *and* `src/firebaseConfig.js` empty/typo'd | `node scripts/verify_deploy.mjs -Url …` reads `configSource`/`missingEnv`; fix the committed file or set a real env value, then redeploy |
| Empty grade/subject dropdowns | The curriculum bundle is not being served | Same script — it fetches the very files the dropdowns need |
| `/build-info.json` or `/curriculum/schedules/*` returns HTML | Production is deploying a **different branch** | Phase 6.3 |
| Old data in a returning browser | Service worker serving the old cache | Compare the deploy's `bundleHash` with `public/curriculum/_BUILD_REPORT.json` |
| Everything works for the admin, not for a member | The un-filtered-list bug, or an index only the member's query path needs | Always test as a member |
| `storage/unknown` on Save to library | The project has no Storage bucket | Expected without Blaze; the app says so. See Phase 2.5 |
| Deploy points at the wrong Firebase project | A blank-or-real env override beat the committed value, or vice versa | `/build-info.json` → `projectId` + `configSource`; delete stray env vars or fix `.env.local` |

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
  "prompt": "Find 35% of GH240.",
  "answer": "GH84",
  "marks": 2,
  "source": "authored"
}
```

> Keep prompts and answers inside WinAnsi (see Part 11). The cedi sign `GH₵` and many symbols are
> **not** printable by jsPDF's font — write "GH" or "cedis" in words. The starter-bank guard test
> will fail a question that cannot be printed.

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
| `firebaseConfigSource.js` | the env-vs-committed rule: `resolveFirebaseConfig()`, `missingEnvNames()`, the six names |
| `examPaper.js` | `SECTION_PLAN`, `sectionBudgets()`, `composePaper()`, `termScope()`, `coverageOf()`, `groupMissing()` — the exam builder's whole brain |
| `questionPaper.js` | renders a composed paper to PDF (student + teacher copies) |
| `starterBank.js` | reads the served bundle and imports questions into Firestore |
| `lessonPlanDocx/Pdf.js`, `schemeDocx/Pdf.js`, `noteDocx/Pdf.js` | the exporters |
| `docxShared.js`, `htmlBlocks.js` | shared Word helpers and rich-text → Word blocks |
| `quizPptx.js`, `lessonSlidesPptx.js` | PowerPoint generation |
| `generatedDocs.js` | the document library: upload, list, open, delete, **and the no-Storage handling** |
| `academicCalendar.js` | the Ghana academic calendar (pure/static) |
| `week.js`, `grades.js`, `subjectThemes.js`, `teachingModels.js`, `lessonTemplate.js`, `docIds.js`, `offlinePack.js` | small pure helpers |
| `authError.js`, `dataError.js`, `profile.js`, `setupGuidance.js` | the wording and shape of the first screens a new deployment meets |

### 9.4 Conventions that will bite you if you ignore them

- **"Adjust state during render", not in an effect.** React's `react-hooks/set-state-in-effect`
  rule is an *error* here (the React Compiler is enabled). When state must reset because a
  derived value changed, do it with a "last seen" guard during render.
- **Effects are for subscriptions only** — `onSnapshot`, listeners — and must return their
  unsubscribe. Guard a `getDoc().then()` with an `active` flag.
- **Every Firestore write stamps `authorId: user.uid` and `serverTimestamp()`.**
- **`import.meta.env` is read at build time.** A new variable means Vercel *and* `.env.local`, and
  it must be added to `FIREBASE_ENV_NAMES` in `firebaseConfigSource.js` if it is one of the six.
- **The six config names live in exactly one place** (`src/lib/firebaseConfigSource.js`).
  `src/firebase.js`, `src/firebaseConfig.js`, `SetupNotice.jsx`, `.env.example` and the two
  verify-deploy scripts all agree with it, and tests fail if they drift. Add a name there, nowhere
  else.
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
filtered + ordered query needs a composite index. `firestore.indexes.json` lists **18**, and
`src/firestoreIndexes.test.js` derives them from the app's queries so a new one cannot be
forgotten (and so a single-field entry — which Firestore rejects on deploy — cannot be added).

**The committed config does not weaken this**, but it raises the stakes on it: the production
project id and API key are public (they always were, in the bundle), so anyone can point a client
at the project. The rules and the Authorized Domains list are the *only* thing standing between
that client and the data. Before you rely on this in production, confirm the rules are actually
**published** (Phase 5) and Authorized Domains has no wildcards (Phase 2.3).

Read `docs/security.md` for the threat model and `docs/gotchas.md` for the list of ways this has
gone wrong in practice — both are short and worth your time before you touch the rules.

---

## Part 13 — Offline behaviour (the PWA)

- **What is cached**: the app shell and the ~39 MB curriculum bundle, under a cache named
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
| Unit + contract | `yarn test` (421 tests, 25 files) | pure logic (`examPaper`, `generatedDocs`, `profile`, `week`, `firebaseConfigSource`, …), the config parity (`firebaseConfig.test.js`), the rules *files* as text (`firestoreRules.test.js`, `storageRules.test.js`), the bundle's integrity, the sidebar/router contract, the index contract, the deploy-script contract, the WinAnsi guard |
| Rules emulator | `yarn test:rules` (against `demo-beacon-rules`; exact count printed at run time) | real permission decisions: a pending member refused, an un-filtered list denied, a like unable to inflate its tally, uploads capped and owner-only. Needs **Java 21** |
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
| 1 | Blank page, nothing in the UI | A missing Firebase config used to throw during module evaluation | Fixed: `main.jsx` renders `SetupNotice` when no config resolves. If you see a blank page, check the browser console for a *new* cause |
| 2 | Every list empty, console says `permission-denied` | A read rule that inspects document fields breaks **list** queries — Firestore needs the rule provable for every candidate document | Give the rule a document-independent branch (`isApprovedOrAdmin()`), or make the query carry a matching `where(...)` |
| 3 | Same, but only for ordinary members | You are testing as an admin, who passes branches members do not | Always verify as a member |
| 4 | Empty list, console says `failed-precondition` | A composite index is missing | Use the **Create the missing index** button on the error, or `firebase deploy --only firestore:indexes`. `src/firestoreIndexes.test.js` should have caught it |
| 5 | Local `yarn dev` writes to production when you expected a sandbox | The committed config is the default; you never overrode it | Put your project's six values in `.env.local` (Phase 3), or blank `src/firebaseConfig.js` locally (Phase 1.0) |
| 6 | `/build-info.json` returns HTML; schedules missing; old `sw.js` | Production is deploying a different branch (Vercel's Production Branch, `main` by default) | Phase 6.3 |
| 7 | Rules deploy "succeeds" but nothing changes | `.firebaserc` points at a different project than the app uses | `node scripts/verify_deploy.mjs` compares them; `firebase use <the app's project>` |
| 8 | Every library upload denied | `storage.rules` never published (or `matches()` written without a trailing `.*` — RE2 matches the *whole* string) | Publish `storage.rules`; end patterns with `.*` |
| 9 | `auth/operation-not-allowed` on sign-up | Email/Password provider not enabled | Phase 2.3 |
| 10 | `auth/unauthorized-domain` | The deployed domain is not in Authorized Domains | Phase 2.3 |
| 11 | Signed in but the portal says "Awaiting approval" with no name/school | Sign-up ran before the rules were published: the Auth account exists, the `users/{uid}` row does not | The portal offers **"Finish setting up your account"**; publish the rules to stop it recurring |
| 12 | A question renders as `\u0000` pairs in a PDF | A character jsPDF cannot encode in WinAnsi | Word the symbol; the guards are in `starterBank.test.js` |
| 13 | An env value "disappears" although you can see it in `.env.local` | PowerShell wrote the file as UTF-16, or added a BOM that ate the first line | Write it as UTF-8 **without** BOM (Phase 3.1); or rely on the committed config |
| 14 | `cat`/`ls` fails inside the build, or `bundleHash` is `null` on Windows | A build plugin used a Unix shell command | Use Node APIs (`node:fs`) in `vite.config.js`; there is a test forbidding shell commands there |
| 15 | `yarn` refuses: *"packageManager: yarn@4.9.4, current version 1.22.22"* | Global Yarn 1, Corepack not enabled | `corepack enable`, reopen the terminal, or use `corepack yarn …` |
| 16 | `firebase: The system cannot find the path specified` | A stale global shim | Use `npx --yes firebase-tools@15.30.2 …` |
| 17 | Rules tests fail on your machine, pass in CI | No JVM | `yarn test:rules` needs Java 21; CI has its own job for it |
| 18 | `make check` exits 2 with a diff under `public/curriculum/` | The committed bundle is stale after a data change | `make build-curriculum`, then commit the bundle **and** `data/inventory.json` |
| 19 | Windows checkout shows every rules test failing | CRLF line endings vs an LF parser | Fixed: the rules tests normalize on read. If you write a new `;\n` parser, normalize too |
| 20 | A generated question has the wrong answer | A generator rule computed it wrongly (e.g. a fraction's operands swapped) | Re-run the answer-verification pass: recompute from the prompt text, then add a regression case |
| 21 | `firebase deploy` ends with `HTTP Error: 400, this index is not necessary` | `firestore.indexes.json` contains an entry with a **single field** — Firestore creates single-field indexes itself | Delete that entry (an unfiltered `orderBy` needs no entry; a filtered + ordered query needs two fields or more) and re-run the deploy — it is idempotent. `src/firestoreIndexes.test.js` fails on one now |
| 22 | `[W] Unused function: …` on every deploy | A rule helper nothing calls | Remove it, or use it. An always-present warning hides the next, real one; `src/firestoreRules.test.js` now fails on an uncalled function |
| 23 | The live site shows **Firebase configuration is missing** instead of the portal | The build resolved **no** config: environment blank *and* `src/firebaseConfig.js` empty or typo'd (this is now rare — the committed fallback prevents the old "empty Vercel variable" cause) | `GET <domain>/build-info.json` → `firebaseConfigured`, `missingEnv`, `configSource`. Fix the committed file or set a real env value, then *Deployments → Redeploy* |
| 24 | A blank Vercel variable seemed to override a good value | Vite lets `process.env` win over `.env` files, so an empty variable beat the file | Fixed by design: a blank env value is treated as absent and falls back to the committed config; the build log names blank variables (`envBlankNames`). Delete empty variables to keep the log quiet |
| 25 | `verify_deploy` says the build is fine but it describes an old commit | With `-SkipBuild` it reads the existing `dist/build-info.json`, which may predate `HEAD` | Run `yarn build` first; confirm `build-info.json`'s `commit` equals `git rev-parse --short HEAD` |

The full, longer list — with the reasoning — is `docs/gotchas.md`. It is the most valuable file in
the repository after this one.

---

## Part 16 — Command reference

**Daily development**

```powershell
yarn install              # dependencies (after a pull that touched package.json/yarn.lock)
yarn dev                  # dev server           → http://localhost:5199  (talks to whatever config resolves!)
yarn build                # production build     → dist/ (+ build-info.json)
yarn preview              # serve the build      → http://localhost:4173  (only place the PWA exists)
yarn lint                 # ESLint — must be clean
yarn test                 # unit + contract tests (421)
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
node scripts/verify_deploy.mjs -SkipBuild                       # config + project parity, no network
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
| `Skill2.md` (this file) | building the project from nothing, corrected for the committed-config behaviour |
| `SKILL.md` | the previous revision (still accurate except for the setup-notice/config drift noted here) |
| `README.md` | the short version: what it is, quick start, command table |
| `docs/features.md` | every feature, page by page, with its route and its rules |
| `docs/architecture.md` | how the app is put together and why |
| `docs/data-model.md` | every Firestore collection and field |
| `docs/security.md` | the threat model and the role matrix |
| `docs/gotchas.md` | **the failures that really happened**, and how to avoid them |
| `docs/curriculum-data.md` | the three data layers, the counts, and what is audited vs extraction-only |
| `docs/build-deploy.md` | Firebase console setup, environment variables, Vercel, the update workflow |
| `docs/verification.md` | the deploy checklist and the symptom → cause table |
| `docs/pwa-offline.md` | the service worker and offline behaviour |
| `docs/conventions.md` | the coding conventions the linter enforces |
| `docs/playbooks.md` | procedures for recurring tasks |
| `docs/TODO.md` | what is done, what is open, and what was decided (the project's memory) |
| `docs/code-bible.md`, `docs/project-blueprint.md` | the original design documents |
| `docs/NACCA_QUESTION_BANK.yaml` | the question-bank specification |

`git-dictionary.md` and `project.md` are the owner's files — read them, but do not edit them.

> **Also stale in the previous docs:** `docs/build-deploy.md` (around line 35) still says "a fresh
> clone has none, and the app shows the setup notice until the six values are there." With the
> committed config that is no longer true — a fresh clone is configured against production. If you
> maintain the docs, fix that line to match Phase 3.1 here.

---

## Part 18 — Phases at a glance (print this)

```
Phase 0   Understand: React PWA + Firebase backend + Python data pipeline. No server to run.
          Config resolves env-first, committed-file fallback → a fresh clone is ALREADY live.
Phase 1   Tools: Git, Node 22, corepack enable (Yarn 4), Python 3.11+.
          git clone --branch arena/01a0af88-beacon-consult …
          yarn install && yarn test && yarn lint.  yarn dev → 5199 → the PORTAL (not a notice),
          pointed at production. Decide before you write anything (Phase 1.0).
Phase 2   Firebase console (only for YOUR project): create project → Firestore (Native, Production)
          → Authentication (Email/Password ON, tight Authorized Domains) → register Web app
          → [optional: Storage, needs Blaze] → .firebaserc = your project id.
Phase 3   OPTIONAL override: .env.local with your six VITE_FIREBASE_* (UTF-8, no BOM, no quotes)
          → restart dev. node scripts/verify_deploy.mjs -SkipBuild → config resolves, projects match.
Phase 4   Sign up in the app → console: users/{uid} → role: "admin", status: "approved" → reload.
          (Rules before sign-up, or use "Finish setting up your account".)
Phase 5   npx firebase-tools login → use <project> → deploy --only firestore:rules,firestore:indexes
          [→ deploy --only storage if enabled].  yarn test:rules.
Phase 6   Vercel: env vars OPTIONAL (committed config is enough) → Production Branch = arena branch
          → Redeploy.
Phase 7   yarn build → node scripts/verify_deploy.mjs -Url <deploy>  (all green; commit == HEAD)
          docs/verification.md section 2, as an ordinary member (throwaway account on prod).
Phase 8   Data: make build-curriculum → commit bundle + inventory; questions via data/questions.
```

**Where the value is, if you are deciding what to do next:** the curriculum dataset and the
question bank (Phase 8) are the parts nobody else has; the portal around them is what makes them
usable in a classroom with intermittent internet. Whatever you build, keep the offline path
working — a teacher with no connection is the user this was designed for.

---

## Corrections in this revision

What `Skill2.md` changes relative to the previous `SKILL.md`, and why. Each was verified against the
repository at commit `a98c94b` (clean tree; `yarn lint` exit 0; `yarn test` 421/421 passing;
`node scripts/verify_deploy.mjs -SkipBuild` exit 0).

1. **Fresh-clone behaviour (the big one).** The old guide said a clone with no `.env.local` "shows
   the setup notice" and that Phase 1 needs "no cloud account." Since `src/firebaseConfig.js`
   committed the real values and `src/firebase.js` falls back to them, a fresh clone boots the
   **full app against production** `beacon-edu-consult-proj`. `main.jsx:19` renders `SetupNotice`
   only when `firebaseConfigured` is false, which now requires *both* sources blank. Fixed in the
   header, Phase 0 (new "How the app gets its config" section), Phase 1.0 (new safety table),
   Phase 1.3, Phase 1 *Done when*, Phase 3.1, Phase 6, and Part 18.
2. **`docs/build-deploy.md:35` carries the same stale claim.** Flagged in Part 17 (not edited here —
   this document reports it; fixing the source doc is a separate change).
3. **Composite-index count.** Part 12 said "19"; `firestore.indexes.json` actually has **18**
   (`node -e "require('./firestore.indexes.json').indexes.length"` → 18), matching the Phase 5
   table. Corrected to 18 everywhere.
4. **`src/lib/` module count.** The tree said "25 modules"; there are **27** non-test `.js` files.
   Corrected, and `firebaseConfigSource.js` / `setupGuidance.js` / `offlinePack.js` are now named.
5. **Rules-check count was self-contradictory** (97 in Phase 5.3 vs 95 in Part 14). Neither is
   verifiable without running the Java emulator, so both are replaced with "the count the run
   prints" rather than a number that will drift again.
6. **Test count** unified at **421** (the old copy variously said ~384 and ~421; the suite reports
   421 passed, 25 files).
7. **`dist/` staleness.** Added an explicit warning (Phase 3.3, 6.4, Part 15 row 25) that
   `verify_deploy -SkipBuild` reads whatever `dist/build-info.json` already exists, which can
   predate `HEAD` — observed live: `dist` reported commit `83930bb` while `HEAD` was `a98c94b`.
8. **Security framing of the committed config.** Added an honest trade-off note (Phase 2.4) and a
   Part 12 paragraph: committing public identifiers is fine *because* they were already public, but
   it makes the published rules + tight Authorized Domains the sole barrier, and repointing the
   project now means editing source, not a dashboard variable.
9. **Tree and conventions** updated to list `src/firebaseConfig.js`, `.env.example`, `vite.config.js`
   and the "six names live in one place" invariant enforced by `firebaseConfigSource.js` and its tests.
