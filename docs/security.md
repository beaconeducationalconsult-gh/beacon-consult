# 3. Security & auth

Security lives in **two** places that must agree:

1. **Client gate** (`ProtectedLayout` in `App.jsx`) — UX only; controls what renders.
2. **`firestore.rules`** — the real enforcement; the database rejects unauthorized
   reads/writes regardless of the UI.

Never rely on the client gate alone. If a rule is missing, the feature is either broken
(denied) or insecure — see the `articles` gap in [gotchas.md](gotchas.md).

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
```

`isApproved()`/`isAdmin()` do a `get()` on the caller's `users` doc — a documented pattern
in Firestore (billed as a read; fine at this scale).

## The access pattern (applies to most collections)

- **read:** `isApprovedOrAdmin()` (+ visibility/status/ownership checks where relevant)
- **create:** `isApprovedOrAdmin()` and `request.resource.data.authorId == request.auth.uid`
  (you can only create docs authored by yourself)
- **update:** author or admin — *except* like/react fields, which any approved member may
  change, enforced with `diff().affectedKeys().hasOnly([...])`
- **delete:** author or admin

### Per-collection notes

- **`users`**: read own always; read others if approved/admin; update self or admin; delete
  admin only.
- **`posts`**: any approved member may like (diff limited to `likedBy`,`likesCount`).
- **`notes`**: read gated by `status=='published'` OR owner/admin; like/dislike diff limited
  to `likes`,`dislikes`. Has `comments` subcollection (approved read/create; author/admin
  delete).
- **`lesson_plans` / `weekly_forecasts`**: read if `visibility=='public'` OR owner.
- **`lesson_slides`**: read if `status=='published'` OR owner/admin. Has `comments`.
- **`vacancies`**: read if `status=='published'` **without auth** (public page) OR
  owner/approved.
- **`progress/{uid}`**: fully private — `read,write` only if `request.auth.uid == uid`.
- **`quote_likes/{quoteId}`**: approved read; create requires `count==1` + only your uid;
  update only permits adding/removing **your own** uid with `count` moving ±1 in step
  (guarded by `hasAll` + `size()` checks so no one can tamper with others' likes).

## Deploying rules

Rules and indexes are **not** deployed by Vercel. After changing `firestore.rules` or
`firestore.indexes.json`, deploy with the Firebase CLI:

```
firebase deploy --only firestore:rules,firestore:indexes
```

(There is no `.firebaserc` committed — add `--project <id>` if the CLI can't resolve the
project.) A committed rules change that hasn't been deployed does **nothing** in
production.
