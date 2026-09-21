# 3. Security & auth

Security lives in **two** places that must agree:

1. **Client gate** (`ProtectedLayout` in `App.jsx`) — UX only; controls what renders.
2. **`firestore.rules`** — the real enforcement; the database rejects unauthorized
   reads/writes regardless of the UI.

Never rely on the client gate alone. If a rule is missing, the feature is either broken
(denied) or insecure. Every collection the portal reads or writes has a rule — the table in
[data-model.md](data-model.md) lists them; a collection added without one is denied in
production until a rule is deployed.

## Auth flow

- **Provider:** Firebase Auth, email/password. Configured in `src/firebase.js`.
- **`AuthContext`** (`src/context/AuthContext.jsx`) exposes `{ user, profile, loading, logout }`:
  - `onAuthStateChanged` sets `user`.
  - When signed in, it **streams** `users/{uid}` via `onSnapshot` into `profile`.
  - `profile === undefined` = still loading; `profile === null` = no profile doc.
- **Sign-up** (`SignUp.jsx`) creates the auth user **and** a `users/{uid}` doc with
  `status: 'pending'`.
- **Sign-in** (`Login.jsx`) → redirects into `/portal`.

## Member states & roles

Stored on `users/{uid}`:

| Field | Values | Meaning |
|---|---|---|
| `status` | `pending` → `approved` → `suspended` | Access lifecycle; set by admins in `Members.jsx` |
| `role` | `member` \| `admin` | `admin` bypasses approval and can moderate/delete anything |

Client gate outcome (`ProtectedLayout`):
- not signed in → `/login`
- `suspended` (non-admin) → `<PendingApproval suspended />`
- not `approved` (non-admin) → `<PendingApproval />`
- `approved` or `admin` → the portal

## Rules helpers (`firestore.rules`)

```
isSignedIn()          request.auth != null
isApproved()          signed in AND users/{uid}.status == 'approved'
isAdmin()             signed in AND users/{uid}.role == 'admin'
isOwner(uid)          request.auth.uid == uid
isApprovedOrAdmin()   isApproved() || isAdmin()
isPro()               active subscriptions/{uid}            (removed; restore it with the
                                                          client that writes subscriptions/{uid} —
                                                          an unused function warns on every deploy)

onlyChanged(keys)     diff().affectedKeys().hasOnly(keys)
changedKeys()         diff().affectedKeys()
likeDelta(field)      a like/unlike moves the tally ±1 and only adds/removes the caller
keepsAuthor()         the update does not hand the document to a different author
```

`isApproved()`/`isAdmin()` do a `get()` on the caller's `users` doc — a documented pattern
in Firestore (billed as a read; fine at this scale). On a missing `users/{uid}` the `get()`
errors, which evaluates to false, so an account with no profile is denied everywhere.

**`users` create is the one rule that must never be relaxed.** It forces `status:'pending'`
and `role:'member'`. Drop those two conditions and any signed-in client can write itself
`status:'approved'` (or `role:'admin'`) and bypass every other rule in the file — `isApproved()`
and `isAdmin()` both read the very document the caller just created.

## The access pattern (applies to most collections)

- **read:** `isApprovedOrAdmin()`, plus a document-independent disjunct where public or
  ownership widening is needed. **Never** nest the member check behind a `resource.data`
  condition on a collection the client lists un-filtered — that denies the whole query.
- **create:** `isApprovedOrAdmin()` and `request.resource.data.authorId == request.auth.uid`
  (you can only create docs authored by yourself)
- **update:** author or admin — *except* like/react fields, which any approved member may
  change, enforced with `diff().affectedKeys().hasOnly([...])`
- **delete:** author or admin

### Per-collection notes

- **`users`**: read own always; read others if approved/admin; update self or admin; delete
  admin only. Create is constrained (see above). `role`/`status`/`schoolId` are admin-only
  fields — the self-service update path cannot change them.
- **`posts`**: any approved member may like — the diff is limited to `likedBy`,`likesCount`
  **and** the tally is checked with `likeDelta`.
- **`notes`**: read is `isApprovedOrAdmin()` **and** the document must be visible to the
  reader — `isAdmin() || isOwner(authorId) || visibility in ['members','public']`, so a note
  saved `visibility: 'private'` is the author's draft. The list pages scope their queries to
  match (Mine / Shared) — see gotchas.md. Like fields diff-limited to
  `likes`,`likesBy` and checked with `likeDelta`. Has a `comments` subcollection (approved
  read/create; author/admin delete).
  *The note-like UI is not built, so nothing writes these fields yet. They are `likes`+`likesBy`
  to match the app-wide counted-array pattern (`posts`, `articles`) — a pair of bare
  `likes`/`dislikes` counters could not be tamper-checked. Change both the rule and this line
  together if that design wins.*
  *`NoteForm` writes `visibility` ('members' | 'public' | 'private') and now does set
  `status` ('published', or 'draft' for private). `status` still cannot gate reads: notes
  written before 2026-09-19 have no such field, and a status-filtered list would hide them.
  `visibility` is the field the rule reads — every note has carried it since the form existed.*
- **`lesson_plans` / `weekly_forecasts`**: read follows the same document-dependent shape as
  `notes` (`isAdmin() || owner || shared visibility`), and both list pages plus `Search.jsx`
  scope their queries to match. **`lesson_slides`** is still `isApprovedOrAdmin()`: its list is
  un-filtered and its `status` field only orders the UI.
- **`vacancies`**: read if `status=='published'` **without auth** (public page) OR
  owner/approved.
- **`progress/{uid}`**: owner-only read/write in practice. The second read clause (members of
  the owner's school) is Phase 2 and unreachable until `schoolId` is actually set on users.
- **`generated_documents/{id}`** (P3-3): the record of a file a member generated. Read is
  owner-or-admin, so the library lists only the caller's own documents —
  `where('authorId', '==', uid)` — and an un-filtered list is denied, which
  `src/firestoreRules.test.js` checks. Create requires `authorId == uid` **and** a
  `storagePath` inside the caller's own folder (`matches('^generated/<uid>/.*')`). It used to be
  a bare prefix `matches('^generated/<uid>/')`, which denied **every** upload: `matches()` anchors
  the pattern at both ends, so a prefix can never match a real path (see [gotchas.md](gotchas.md)).
  Admin update; owner-or-admin delete. The file itself lives in Cloud Storage — see below.
- **`quote_likes/{quoteId}`**: approved read; create requires `count==1` + only your uid;
  update only permits adding/removing **your own** uid with `count` moving ±1 in step
  (guarded by `hasAll` + `size()` checks so no one can tamper with others' likes).
  Read is approved-only, so like counts are **not** visible to anonymous visitors — the public
  quotes page shows 0 and `useQuoteLikes` swallows the denial.

### Blocks for phases that are not built

`firestore.rules` also carries rules for `generated_materials` (retired with the Material
Service), and for `deliveries`, `subscriptions`, `schools`, `school_codes`, `classrooms`,
`quizzes` and `quiz_attempts` (Phases 1–3). **No client code writes any of them**, so they
enforce nothing that exists. They are design notes: safe to deploy, impossible to verify, and
they must be re-checked against the real code on the day that phase ships — or deleted with it.

## Cloud Storage (`storage.rules`)

Storage holds exactly one thing: the documents members generate (lesson plans, schemes, exam
papers, quiz decks, study notes) so the **library** can hand them back later instead of their
existing only as whatever landed in a downloads folder. Layout — the only paths the rules
allow:

```
generated/{uid}/{timestamp}-{filename}
```

The uid in the path **is** the permission: a member writes under their own uid and nowhere
else, reads back only what they stored (or anything at all, if admin), and may not enumerate
another member's folder. Uploads are capped at 8 MB in the rule, and anything outside
`generated/` is denied — including reads — so a future feature has to add its own rule on
purpose. `src/lib/generatedDocs.js` builds the path; both sides have to agree, and
`src/storageRules.test.js` fails if they stop agreeing.

Two consequences worth knowing:

* **The cross-service `firestore.get()` is deliberate and its rules must match.** Status and
  role live in Firestore, so storage rules call `firestore.get(...)` to read them — the same
  two lookups `firestore.rules` defines, duplicated because there is no shared include. If the
  Firestore helpers ever change, this file changes with them.
* **Storage has no emulator-free proof here.** The emulator needs a JVM, which this
  environment lacks (see P2-1 in docs/TODO.md), so the guarantees above are verified by
  reading the file and by `src/storageRules.test.js`, not by exercising a real upload.

## Deploying rules

Rules and indexes are **not** deployed by Vercel. After changing `firestore.rules`,
`firestore.indexes.json` or `storage.rules`, deploy with the Firebase CLI:

```
firebase deploy --only firestore:rules,firestore:indexes
firebase deploy --only storage
```

`.firebaserc` pins the project (`beacon-edu-consult-proj` — the live one, as of
2026-09-20; the pre-flight fails if it and the app's `VITE_FIREBASE_PROJECT_ID` disagree), so the CLI resolves it
without a `--project` flag; `make deploy-rules` wraps the Firestore half (`make
deploy-storage` wraps the Storage half). A committed rules change
that hasn't been deployed does **nothing** in production.

**Pasting into the Firebase console also works**, and is the fastest way to unblock a fresh
project — but copy from this repo's `firestore.rules`, never from a chat message or a design
doc, because the console copy is not version-controlled and the two drift silently. After
pasting, the console shows the rules as "published"; the repo file is still the source of
truth, so re-run the CLI deploy when you next touch it.

Before publishing, check the two invariants that a rules edit can quietly destroy:

1. `users` create still forces `status == 'pending'` and `role == 'member'`.
2. Every like path still calls `likeDelta(...)` — `hasOnly(...)` alone does not stop a member
   from inflating a tally or stuffing `likedBy` with other people's uids.

`yarn test` checks both, plus that every collection `src/` touches has a match block and that
each authored collection pins `authorId` on create and calls `keepsAuthor()` on update
(`src/firestoreRules.test.js`). Each one was verified by re-introducing the bug and watching it
fail — but those checks are **static**: they prove a guard was not deleted, not that a
permission decision is correct.

The decisions themselves are tested against a real rules engine:

```bash
yarn test:rules        # starts the Firestore emulator, runs tests/rules/, shuts it down
```

`tests/rules/firestore.rules.test.js` and `tests/rules/storage.rules.test.js` ask the emulators
the questions this document answers with prose — can an approved member read a colleague's
private draft (no), does an un-filtered list of `notes` survive for an ordinary member (no), can
a like inflate its own tally (no), can a `generated_documents` record point at another member's
storage folder (no), can a school admin move a member into a school that is not theirs (no), can
a member write a file outside `generated/<uid>/` or past 8 MB (no), can anyone read another
member's file (no — except an admin, yes). It needs Java 21 and the network, so
it is **not** part of `make check`; CI runs it in its own `rules` job. Re-run it before
publishing a rules change, not after.
