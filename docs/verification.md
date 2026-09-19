# 9. Verifying a deploy (P0-4)

A green build proves nothing about rules, indexes, or the service worker. This is the
checklist that does, in two parts: the part a machine can check, and the part a person has
to drive. Run it before a demo, after any change to `firestore.rules` /
`firestore.indexes.json`, and whenever a teacher reports "it doesn't work" on their phone.

## 1. Automated pre-flight

```bash
make deploy-check URL=https://your-deploy.vercel.app     # scripts/verify_deploy.py
```

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
| `storage.rules` (`make deploy-storage`, or paste it under Storage → Rules) | New in P3-3. Without it the library cannot store anything, and every upload is denied |
| Firestore indexes (19; the console offers one-click links on the first error) | The library's list needs `authorId` + `createdAt` |

Publish the Firestore rules **after** the new build is live: the new rules require the scoped
list queries the new build makes.

## 2. The flows (needs a signed-in account on the live project)

Do these in **one ordinary member account** (not an admin — admins pass branches ordinary
members do not; that is how the un-filtered-list bug hid). Tick each row; the "why" column
is what the step is actually testing.

### Sign-up and approval

| # | Step | Passes when | Why |
|---|---|---|---|
| 1 | Sign up a new account | Lands on "pending approval", can browse nothing but the curriculum | `users` create forces `status:'pending'`. A self-approving sign-up would bypass every other rule |
| 2 | In the console set `role:'admin'` on an account, approve the new one from `/portal/members` | The new account can now read content | Only an admin can approve |
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
| 18 | Scroll the bank to the bottom | "Load more" appears while older questions exist; "N shown — that is everything" when they run out | P2-4 paging |
| 19 | Select questions → "Question paper" and "Quiz slideshow" | PDF and PPTX download with the right total marks | |
| 20 | On **Lesson plans**, click a plan's slides link | Deck builds from that week's scheduled lessons | `lesson_slides` |

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
| 26a | Open a lesson plan → **Save to library**; then **My library** → **Open** | The document comes back, byte-identical, and **Delete** removes it | P3-3: the file is in Storage under your own uid, the record in `generated_documents` |

### The teaching models (P3-4)

| # | Step | Passes when | Why |
|---|---|---|---|
| 26b | Curriculum → Mathematics B4 → **Teaching models** | Five models open, each names its indicators, and changing a control changes what a pupil sees | P3-4 — and they work offline, so try one on the school wifi first |

### After a curriculum rebuild

| # | Step | Passes when | Why |
|---|---|---|---|
| 27 | `python3 scripts/build_app_curriculum.py`, rebuild, deploy | A returning browser gets the new data on the next load — no "clear site data" instructions | The cache is named after `bundleHash`, so the new worker renames it and drops the old one |

## 3. Record what you saw

When a step fails, capture: the URL, the account's role/status, and the Firestore error
code (`permission-denied` vs `failed-precondition` tells you rules vs missing index — the
latter also names the index URL in the browser console). File it as a TODO row rather than
fixing it silently in the console.
