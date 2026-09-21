# The five surfaces — where everything lives, and how to check it

This project is not one thing that can be "right" or "wrong". It is five moving parts plus your
browser, and a symptom that looks the same can come from any of them. That is not a theory: in
September 2026 the live site showed **"Firebase configuration is missing"** for three consecutive
deploys, and the cause was in three different surfaces —

1. **Vercel**: the build environment had none of the six `VITE_FIREBASE_*` values, so the first
   production build had no Firebase project to talk to;
2. **the repository**: the committed `.env.production` that was supposed to fix that was written by
   PowerShell **with a byte-order mark**, which hides its first line from Vite's parser — the file
   silently lost the API key;
3. **Vercel again**: six variables existed with *empty* values, and in Vite's loader a blank
   environment variable wins over a file — so the committed values were cancelled too.

This page is the map: what each surface owns, the one check that answers it, and the failure it is
known to produce. It is the first thing to read when something looks wrong.

| Surface | Owns | The check | The failure it produces |
|---|---|---|---|
| **1. GitHub repo** | The source of truth: code, rules, indexes, curriculum JSON, docs | `git pull --ff-only` then `yarn test` (421 tests) | You are reading or deploying older code than you think |
| **2. Firebase / Firestore** | The database, sign-in, and on the server side the **rules** and **indexes** | `npx --yes firebase-tools@15.30.2 deploy --only firestore:rules,firestore:indexes`, then Console → Firestore → Indexes. A raw unauthenticated read is refused (`403 PERMISSION_DENIED`) when the rules are live | Empty lists (`failed-precondition`), "permission denied", or a database still open to everyone |
| **3. Vercel** | Serving the built app at `beacon-edu-consult.vercel.app`, and the build itself | `GET /build-info.json` on the deploy — answers `firebaseConfigured`, `configSource`, `projectId`, `commit` | The setup notice instead of the portal; a deploy serving an older branch |
| **4. Local files** | `.env.local` (optional), `dist/`, `node_modules/`, `.env.production` (removed) | `yarn build && node -e "console.log(require('./dist/build-info.json'))"` | A local build that works while the deploy does not, or the reverse |
| **5. The sandbox** (Arena) | The agent's working copy, bound to the branch `arena/01a0af88-beacon-consult` | `git log --oneline -1` and `git status` | Nothing durable — it is a fresh clone; `/tmp` and `node_modules` are rebuilt |
| **6. Your browser** | A cached copy of the app: HTTP cache, and the **service worker** | Hard reload (`Ctrl+Shift+R`); DevTools → Application → Service Workers → *Unregister* | A page that looks stale — the old build's screen — while the server is already serving the new one |

## The branch model (and why `main` looked stale)

There are exactly **two** branches, and there is nothing stale to delete:

| Branch | What it is | Deployed? |
|---|---|---|
| `main` | The project's branch — the one that matters, and what GitHub shows by default | Yes, once you point Vercel's Production Branch at it |
| `arena/01a0af88-beacon-consult` | The **agent's working branch** — every task is committed here, and only here | Currently yes: Vercel's Production Branch was set to it |

They are not competing: `main` is a straight line through the agent's work, and the agent merges it
forward. Nothing was ever "left behind" on another branch — the one real difference was that `main`
had not been updated since 17 September, which makes the repository *look* like it has two versions
of the project when it only ever had one.

The recommended end state, in order:

1. Merge the open pull request (agent branch → `main`). One click: **Merge pull request** with
   *Create a merge commit* (not squash — the history is worth keeping).
2. Vercel → the project → **Settings → Git → Production Branch** → `main`, then **Redeploy**.
3. Check it: `GET /build-info.json` → `configured: true` and `commit` = the merge commit.

From then on a change reaches the live site the same way every time: the agent pushes to its
branch → opens (or refreshes) a pull request → **you** click *Merge* → Vercel builds `main` and the
site updates. That click is a feature, not a chore: it is the moment a change becomes public, and
it is the only step in the whole pipeline that needs a human.

## The 60-second triage, in this order

```powershell
cd C:\Users\KING\dev-area\beacon-curriculum

git pull --ff-only            # 1. is my copy current?
yarn test                     # 2. does the code agree with itself? (421 tests)

# 3. ask the deploy itself — this is the check that would have saved three rounds
npx --yes vercel@latest --version    # (once, if you want the Vercel CLI handy)
node scripts/verify_deploy.mjs -Url https://beacon-edu-consult.vercel.app
```

Then, in the browser: **hard reload**. If the old screen persists, unregister the service worker
(DevTools → Application → Service Workers) and reload once more. The service worker exists to make
the app work offline; when it is holding an old shell, that is the six-second fix.

Things no script can check, because they are console settings — look at them only when a symptom
points there:

| Symptom | Console page |
|---|---|
| Sign-up refuses with `auth/operation-not-allowed` | Authentication → Sign-in method → **Email/Password** must be *Enabled* |
| Sign-up refuses with `auth/unauthorized-domain` | Authentication → Settings → **Authorized domains** must list `beacon-edu-consult.vercel.app` (and `localhost`) |
| A list is empty with `failed-precondition` | Firestore → **Indexes** — 18 composite indexes, *Enabled* |
| "permission denied" everywhere | The rules are older than the code: `make deploy-rules` |
| You are stuck on the pending-approval screen | Firestore → Data → `users/{your-uid}` → `status: "approved"` (and `role: "admin"` for the admin) |

## What is now guarded, so it cannot come back

Every failure of this kind that has actually happened is now held down by a test or a check, not by
memory:

| Failure | Guard |
|---|---|
| A build with no Firebase values — a green build and a blank site | `src/firebaseConfig.js` is committed source, so **every** build has a config; `dist/build-info.json` reports `configSource` and `firebaseConfigured` |
| A blank environment variable cancelling a committed value | `src/lib/firebaseConfigSource.js` falls back past blanks and reports them; the build log names any it saw |
| A BOM hiding an env file's first line | The values are source now, tested free of BOM/control characters (`src/firebaseConfig.test.js`); `.env.example` warns about UTF-8 |
| A config pointing at a different project than the CLI deploys to | `src/firebaseConfig.test.js` compares the project id with `.firebaserc`; both pre-flight scripts compare it with the app |
| A single-field index that makes the whole indexes deploy fail | `src/firestoreIndexes.test.js` (and `docs/gotchas.md` on the half-deployed state it leaves) |
| A dead rule function warning on every deploy | `src/firestoreRules.test.js` fails on any declared-but-uncalled function |
| A production domain serving a different branch | `scripts/verify_deploy.{py,mjs}` compare served files with this checkout and call out a 200 that is really the app shell |
| A setup notice that told a *visitor* to run `yarn dev` | `src/lib/setupGuidance.js` splits the instructions by where the reader is standing |

## Keeping the sandbox and your machine in step

The sandbox is a clone of the same repository, so there is no state to reconcile — only two
habits:

* **After every task**, run the update block in the reply (`git pull --ff-only`, `yarn install`,
  `yarn test`). The agent's commits are pushed to `arena/01a0af88-beacon-consult` before the reply
  is written, so the pull always has something to take.
* **Nothing secret or machine-specific is committed.** `.env.local` stays local (and is optional
  now); the Firebase web config is committed on purpose, because it is public client config that
  ships in the browser bundle regardless — the security boundary is the rules, the Authorized
  Domains list, and each member's `status` in `users/{uid}`.
