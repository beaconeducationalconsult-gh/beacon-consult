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
isPro()               active subscriptions/{uid}            (INERT — no client yet)

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

- **read:** `isApprovedOrAdmin()` (+ visibility/status/ownership checks where relevant)
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
- **`notes`**: read gated by `status=='published'` OR owner/admin; like fields diff-limited to
  `likes`,`likesBy` and checked with `likeDelta`. Has a `comments` subcollection (approved
  read/create; author/admin delete).
  *The note-like UI is not built, so nothing writes these fields yet. They are `likes`+`likesBy`
  to match the app-wide counted-array pattern (`posts`, `articles`) — a pair of bare
  `likes`/`dislikes` counters could not be tamper-checked. Change both the rule and this line
  together if that design wins.*
- **`lesson_plans` / `weekly_forecasts`**: read if `visibility=='public'` OR owner; `school`
  visibility (Phase 2) compares `schoolId` against the caller's own school.
- **`lesson_slides`**: read if `status=='published'` OR owner/admin. Has `comments`.
- **`vacancies`**: read if `status=='published'` **without auth** (public page) OR
  owner/approved.
- **`progress/{uid}`**: owner-only read/write in practice. The second read clause (members of
  the owner's school) is Phase 2 and unreachable until `schoolId` is actually set on users.
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

## Deploying rules

Rules and indexes are **not** deployed by Vercel. After changing `firestore.rules` or
`firestore.indexes.json`, deploy with the Firebase CLI:

```
firebase deploy --only firestore:rules,firestore:indexes
```

(There is no `.firebaserc` committed — add `--project <id>` if the CLI can't resolve the
project.) A committed rules change that hasn't been deployed does **nothing** in
production.

**Pasting into the Firebase console also works**, and is the fastest way to unblock a fresh
project — but copy from this repo's `firestore.rules`, never from a chat message or a design
doc, because the console copy is not version-controlled and the two drift silently. After
pasting, the console shows the rules as "published"; the repo file is still the source of
truth, so re-run the CLI deploy when you next touch it.

Before publishing, check the two invariants that a rules edit can quietly destroy:

1. `users` create still forces `status == 'pending'` and `role == 'member'`.
2. Every like path still calls `likeDelta(...)` — `hasOnly(...)` alone does not stop a member
   from inflating a tally or stuffing `likedBy` with other people's uids.
