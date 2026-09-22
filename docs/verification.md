# 9. Verifying a deploy (P0-4)

A green build proves nothing about rules, indexes, or the service worker. This is the
checklist that does, in two parts: the part a machine can check, and the part a person has
to drive. Run it before a demo, after any change to `firestore.rules` /
`firestore.indexes.json`, and whenever a teacher reports "it doesn't work" on their phone.

## 1. Automated pre-flight

```bash
make deploy-check URL=https://your-deploy.vercel.app     # scripts/verify_deploy.py
node scripts/verify_deploy.mjs -Url https://your-deploy.vercel.app   # same checks, Node only
.\scripts\deploy_check.ps1 -Url https://your-deploy.vercel.app       # the same, from PowerShell
```

The two are peers — same checks, same exit code — because the machine that deploys is Windows
and may not have Python; `src/deployCheck.test.js` fails if they drift apart. Run it from the
repository root; without `-Url` it only checks the local half (`.env.local`, a build, the bundle
hash), which is the part that catches a missing config before anything is deployed.

It fetches the deploy (no browser, no Firebase credentials) and fails with an explanation
for each of these:

| Check | Catches |
|---|---|
| `GET /build-info.json` → `firebaseConfigured` | **P0-1**: a deploy built without the six `VITE_FIREBASE_*` values. The app then shows the setup notice instead of the portal, and the Vite build is still green |
| `build-info.json` → `bundleHash` vs the local `public/curriculum/_BUILD_REPORT.json` | A deploy serving an older curriculum than this checkout |
| `GET /` returns the SPA shell | A broken Vercel rewrite (every deep link 404s) |
| `GET /curriculum/grades.json` and `/curriculum/schedules/b1-mathematics.json` | A rewrite that swallows the bundle, so grade/subject dropdowns and planners come up empty |
| `GET /sw.js` reads `bundleHash` | An old build whose service worker still caches under a hand-bumped name |

`make check` runs the offline half (`scripts/verify_deploy.py --offline-check`), which only
asserts that the local bundle hash exists and that `sw.js` still reads it.

### Rules and indexes to publish first (P0-2 / P3-3)

Nothing below can pass until the console matches this checkout:

| Publish | Why now |
|---|---|
| `firestore.rules` (paste into the console, or `make deploy-rules`) | It carries the visibility-gated reads for `/notes/`, `/lesson_plans/` and `/weekly_forecasts/` (P2-4/P2-7) **and** the `generated_documents` block added for the document library (P3-3). The console copy predates both |
| `storage.rules` (`make deploy-storage`, or paste it under Storage → Rules) — **only if the project has a Storage bucket** | New in P3-3. Without it the library cannot store anything, and every upload is denied. No bucket (Spark plan)? Skip this one and `make deploy-storage`; the library stays off and says so |
| Firestore indexes (19; the console offers one-click links on the first error) | The library's list needs `authorId` + `createdAt` |

Publish the Firestore rules **after** the new build is live: the new rules require the scoped
list queries the new build makes.

### The order, for a first deploy on a fresh project

Four things have to happen, and three of them are on this side — the Vercel build does not
touch the database. **On a project that was just created, do the console setup first** — the
database, the Email/Password provider, the Storage bucket and the web app registration are all
prerequisites, with the error each one causes when missing: see *Setting up a new Firebase
project* in [build-deploy.md](build-deploy.md).

| # | Do | Passes when |
|---|---|---|
| 1 | Put the six `VITE_FIREBASE_*` values in **Vercel → Settings → Environment Variables**, for **Production *and* Preview**, then deploy | `node scripts/verify_deploy.mjs -Url <deploy>` says *the deploy has its Firebase config*. A deploy built without them is green and shows the setup notice instead of the portal |
| 2 | Deploy the build (push, or `vercel --prod`) | The same run says *serving the curriculum this checkout builds* and *the SPA shell is served* |
| 3 | Publish the rules and the indexes — `make deploy-rules` (Firestore rules + 18 indexes) and `make deploy-storage` (Storage rules), or paste `firestore.rules` / `storage.rules` into the console. **Check `.firebaserc` first**: the pre-flight says whether the CLI's project is the one the app talks to, and it follows `.firebaserc`, not `.env.local` | Step 4 stops failing with `permission-denied`. The console copy most projects have predates the visibility-gated reads, the `generated_documents` block, and the `matches()` fix |
| 4 | Create an account, set `role:'admin'` + `status:'approved'` on its `users/{uid}` doc (P0-3), approve a second account, then walk section 2 | The flows below pass for an **ordinary member**, not just an admin |

Step 3 comes after step 2 for a reason: publishing the rules before the new build is live turns
an old client's list pages from "shows everything" into `permission-denied`.

The rules can also be asked directly, before publishing anything:

```bash
yarn test:rules     # Firestore + Storage emulators, tests/rules/ (needs Java 21)
```

That suite is the permission matrix — a pending member refused, an un-filtered list denied, a
like unable to inflate its tally, a library record unable to point at another member's folder,
and the files themselves: an upload only under your own uid, the 8 MB cap, reads owner-or-admin,
everything outside `generated/` denied. It needs a JVM and downloads firebase-tools plus the
emulator jars, which is why it is not part of `make check`; CI runs it in its own job.

## 2. The flows (needs a signed-in account on the live project)

Do these in **one ordinary member account** (not an admin — admins pass branches ordinary
members do not; that is how the un-filtered-list bug hid). Tick each row; the "why" column
is what the step is actually testing.

### Sign-up and approval

| # | Step | Passes when | Why |
|---|---|---|---|
| 1 | Sign up a new account | Lands on "pending approval", can browse nothing but the curriculum | `users` create forces `status:'pending'`. A self-approving sign-up would bypass every other rule |
| 2 | In the console set `role:'admin'` on an account, approve the new one from `/portal/members` | The new account can now read content | Only an admin can approve |
| 2a | Sign up **before** the rules are published (or with a suspended account) | The portal offers **"Finish setting up your account"** with a button that creates the pending row — not a dash-filled "Awaiting approval" | The two-write sign-up: Auth first, Firestore second. The recovery uses the one self-create the rules allow (`status:'pending'`, `role:'member'`) |
| 3 | As the new member, open an incognito window and visit `/articles` | Public articles load **without** signing in | The anonymous read path is the only one the public sees |

### Scheme (weekly forecast)

| # | Step | Passes when | Why |
|---|---|---|---|
| 4 | `/portal/forecasts/new` → pick grade + subject + term → "Use N scheduled weeks" | Weekly rows arrive within a second or two | Loads exactly one `schedules/<grade>-<subject>.json` (~0.5 MB), not the whole grade (P2-3) |
| 5 | Save, then reopen it from **Mine** | Rows and notes come back | Round-trip through `weekly_forecasts` |
| 6 | Reopen, edit a row, save | The edit survives a reload | `keepsAuthor()` lets an owner update without rewriting `authorId` |
| 7 | Delete it | Disappears from both tabs after a reload | Delete rule |

### Lesson plan

| # | Step | Passes when | Why |
|---|---|---|---|
| 8 | `/portal/curriculum/B4/mathematics` → pick an indicator → "Plan a lesson" | The form opens with the indicator, strand and sub-strand filled in | The curriculum→planner deep link |
| 9 | Fill the phases, save | Plan appears under **Mine** | |
| 10 | Open the plan → **Word** and **PDF** | Both files download and open; A4, footer with school/teacher | The exporters (`docxExport.test.js` covers the Word half) |
| 11 | Put a `?from=<another plan's id>` on `/portal/plans/new` | It prefills from the other plan | Cloning |

### Private drafts (P2-7 — **newest rules**, test carefully)

| # | Step | Passes when | Why |
|---|---|---|---|
| 12 | Create a note and a scheme with **"Only me (draft)"** | Each saves; each appears under **Mine** | `visibility: 'private'` |
| 13 | Open the **Shared** tab for notes and schemes | Neither draft is listed | The Shared query is `visibility in ['members','public']` |
| 14 | Log in as a *different* approved member and open the draft's URL directly | "Not found" / permission denied | The read rule, not just the query |
| 15 | Search for the draft's title as that other member | No hit | `Search.jsx` asks for the author slice plus the shared slice only |
| 16 | Switch the draft back to "Members of the network" | It appears in Shared for the other member | |

> **Deploy order.** If the shared lists come back empty for everyone, or every list shows a
> permission error, the rules and the build are out of step: the new rules require the new
> queries. Publish rules *after* the new build is live, and deploy
> `firestore.indexes.json` at the same time (see gotchas.md).

### Question bank, quiz, slides

| # | Step | Passes when | Why |
|---|---|---|---|
| 17 | `/portal/questions/new` → add 3 questions | They appear in the bank | |
| 17a | Question bank → **Starter bank** → import *Mathematics B4* | It reports 187 questions over 71/71 indicators, and the bank shows them with `source: starter-bank` | `src/lib/starterBank.js` — the served bundle is what seeds a new project, not the curriculum files |
| 18 | Scroll the bank to the bottom | "Load more" appears while older questions exist; "N shown — that is everything" when they run out | P2-4 paging |
| 19 | Select questions → "Question paper" and "Quiz slideshow" | PDF and PPTX download with the right total marks | |
| 20 | On **Lesson plans**, click a plan's slides link | Deck builds from that week's scheduled lessons | `lesson_slides` |

### The exam paper (P1-13 — the newest page)

| # | Step | Passes when | Why |
|---|---|---|---|
| 19a | `/portal/questions/exam` → Mathematics **B2**, 50 marks, term 1 | The preview says **50**, and all three sections have something in them — Section C holds the long-answer items | The paper's marks are the marks asked for: a section that cannot spend its share hands them to the ones that can, and the page names the section it did not use (`too-long` / `no-candidates`) instead of quietly printing short |
| 19b | Switch the term to **2**, then **3** | The scope line changes, and reads **100%** — *"Term 2 schedules 56 indicators — the pool asks about 56 (100%)"* | Term scope is read from `schedules/<grade>-<subject>.json`, the only file that knows what a term teaches |
| 19c | Same page → **B7**, 60 marks | 30/50/60 compose exactly, Section C included | The JHS pool was authored to 100% per term for this |
| 19d | Drop a question, then export **student** and **teacher** PDFs | The paper recomposes without it, and both PDFs download — the teacher copy carries the marking scheme | Composition is pure, so the preview cannot disagree with the PDF |
| 19e | **Save to library**, then open **My library** *(needs Storage — skip if the project has no bucket; the page says why)* | The paper is there and opens | `generated_documents` + Storage, the same path as 26a |

### The BECE mock (P3-6 — the newest page)

| # | Step | Passes when | Why |
|---|---|---|---|
| 20a | `/portal/questions/bece` — nothing to select | The composition card appears on its own: Paper 1 **40 questions · 40 marks**, Paper 2 **6 of 15 marks · answer 4**, total **100** | The page composes from the whole served JHS bank — no grade, term or subject picker, because the BECE examines B7–B9 together |
| 20b | Open **Paper 2 as composed** | Every question's parts sum to exactly 15, lettered (a), (b)… easiest first, and no prompt appears twice anywhere in the mock | A 15-mark question is composed from the bank's 1–5-mark items; a reused item would print the same question against itself |
| 20c | Export **student** and **teacher** PDFs | Paper 1's rubric says answer ALL; Paper 2's says answer four, with marks in the margin; the teacher copy carries the marking scheme for both papers | The sitting counts 4 × 15 = 60 of the 90 the sheet prints — the rubric is where a teacher would notice if that ever drifted |
| 20d | **Save to library** *(needs Storage — same caveat as 19e)* | The mock is in My library and opens | Same path as 26a |

### Notes, progress, calendar

| # | Step | Passes when | Why |
|---|---|---|---|
| 21 | Tick a week in `/portal/progress` | Highlight updates and survives a reload | `progress/{uid}` is owner-only |
| 22 | Open the workspace rail → **Term calendar**, switch grade | Weeks fill in progressively, no long freeze | `useGradeSchedules` pages in the subject files |
| 23 | Add a comment on a note | It appears under the note | `notes/comments` |

### Offline (production build only)

The service worker is registered in production builds only, so this section is
`yarn build && yarn preview`, never `yarn dev`.

| # | Step | Passes when | Why |
|---|---|---|---|
| 24 | Open `/portal/curriculum`, browse two subjects | DevTools → Application → Cache Storage shows one cache named `beacon-<bundleHash>` | P2-3 |
| 25 | DevTools → Network → **Offline**, reload | The app boots; the curriculum you browsed still renders; Firebase-backed lists show the offline/error state, not a blank page | App shell + bundle cached |
| 26 | Back online, reload | The curriculum and lists recover without clearing site data | Firestore's own offline cache |
| 26a | Open a lesson plan → **Save to library**; then **My library** → **Open** | The document comes back, byte-identical, and **Delete** removes it | P3-3: the file is in Storage under your own uid, the record in `generated_documents`. **Needs Storage** (Blaze plan — see build-deploy.md). Without a bucket, skip this row: the button is replaced by a line saying the library is off, and that is the pass |

### The teaching models (P3-4)

| # | Step | Passes when | Why |
|---|---|---|---|
| 26b | Curriculum → Mathematics B4 → **Teaching models** | Five models open, each names its indicators, and changing a control changes what a pupil sees | P3-4 — and they work offline, so try one on the school wifi first |

### After a curriculum rebuild

| # | Step | Passes when | Why |
|---|---|---|---|
| 27 | `python3 scripts/build_app_curriculum.py`, rebuild, deploy | A returning browser gets the new data on the next load — no "clear site data" instructions | The cache is named after `bundleHash`, so the new worker renames it and drops the old one |

## 3. When a row fails

Start from the symptom, because the two Firestore error codes point at completely different
repairs — and the app now says which one it is (the message on the page, and the button beside
it):

| Symptom | Cause | Fix |
|---|---|---|
| "Could not load … (permission-denied)", whole list | The published rules are older than this build, or the account is not approved | `make deploy-rules`, or check the member's `status` in `/portal/members`. Publish **after** the build goes out |
| "Could not load … (failed-precondition)" with a link | A composite index is missing | Click the link → Create index → wait a minute. `src/firestoreIndexes.test.js` is supposed to make this impossible for a shipped query — if it fires, a query was added without its index and the test's scan missed it |
| The setup notice instead of the portal | The **deploy** was built without the six Firebase values. Since `src/firebase.js` falls back to the committed `src/firebaseConfig.js`, this means that file is empty too (or a blank `VITE_FIREBASE_*` variable is worth checking — it counts as absent and the build log names it) | `node scripts/verify_deploy.mjs -Url <deploy>`, or `GET /build-info.json` — `missingEnv` names what is missing and `configSource` says where the values came from (`env`, `committed`, `mixed`). Fill `src/firebaseConfig.js`, or set the variables on Vercel for Production **and** Preview and **redeploy** — a variable change does not rebuild anything on its own |
| Grade or subject dropdowns come up empty | The curriculum bundle is not being served | `node scripts/verify_deploy.mjs -Url <deploy>` — it fetches the two files the dropdowns need |
| A returning browser shows old data after a curriculum rebuild | The service worker is serving the old cache | Check the deploy's `bundleHash` against `public/curriculum/_BUILD_REPORT.json`; the new worker renames the cache |
| `/build-info.json` or `/curriculum/schedules/*` returns the app's HTML, or a curriculum file is much smaller than the same file in this checkout | The **production domain is deploying a different branch** — Vercel deploys the Production Branch (`main` by default) to it, and `main` is still the old snapshot, so everything that exists in both branches looks healthy while anything new answers with the shell | Vercel → Settings → Git → **Production Branch** → `arena/01a0af88-beacon-consult` (or publish to `main`), redeploy, then re-run the pre-flight. The check compares sizes and shapes with this checkout and says which file is missing |
| Everything works for the admin and not for a member | The un-filtered-list bug, or an index the admin's query path does not need | Drive section 2 as an ordinary member, never as the admin who built it |

Record what you saw before fixing it: the URL, the account's role/status, and the error code.
File the finding as a TODO row rather than fixing it silently in the console.
