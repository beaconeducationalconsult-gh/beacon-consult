# 6. Conventions & patterns

Match the surrounding code. The conventions below are already pervasive — follow them.

## React patterns

### "Adjust state during render", not effects
When state must reset because a prop/derived value changed, do it during render with a
"last seen" guard — **not** in a `useEffect`. This is used throughout (e.g. `ForecastForm`,
`Wisdom`) and the ESLint rule `react-hooks/set-state-in-effect` will flag the effect version.

```js
const key = `${tab}|${term}`
const [lastKey, setLastKey] = useState(key)
if (key !== lastKey) {
  setLastKey(key)
  setVisible(BATCH)   // reset derived state
}
```
See react.dev/learn/you-might-not-need-an-effect.

### Effects are for subscriptions/external sync only
Use `useEffect` for Firestore `onSnapshot`, event listeners, etc. Always return the
unsubscribe. Guard against unmount with an `active` flag when using `getDoc().then()`.

### Firestore writes
Always stamp `authorId: user.uid` and `serverTimestamp()`. Use `addDoc` for new docs,
`updateDoc` for edits, `setDoc(..., { merge: true })` for create-or-update (e.g. likes with
`increment()` / `arrayUnion` / `arrayRemove`).

### Real-time vs one-shot
List/detail screens that benefit from liveness use `onSnapshot`; one-shot loads use
`getDoc`/`getDocs`. Provide an **error callback** to `onSnapshot` so a rules-denied read
degrades gracefully instead of throwing (see `useQuoteLikes`).

## The Tailwind design vocabulary

Shared component classes are defined in `src/index.css` (`@layer components`). **Use these
instead of re-styling headings/labels every time:**

| Class | Use |
|---|---|
| `.page-title` | Top-of-page `<h1>` (24px bold) |
| `.page-subtitle` | Supporting sentence under a title |
| `.section-heading` | Small uppercase section label |
| `.card-title` | Primary text inside a card |
| `.card-meta` | Secondary/muted info line |
| `.label-caps` | Uppercase field label |

### Colour & style norms
- **Brand:** indigo primary (`indigo-600/700`), amber/gold accents (`amber-500`), cream
  sidebar (`#faf6f1`), slate neutrals. Admin accents are amber.
- Cards: `rounded-2xl border border-slate-200 bg-white shadow-sm`, hover `shadow-md`.
- Inputs: `rounded-md/lg border border-slate-300 … focus:border-indigo-500 focus:outline-none`.
- Icons: inline SVG (`viewBox="0 0 24 24"`, `stroke="currentColor"`, `h-4 w-4`) — no icon lib.
- Theme-aware light styling; the app targets light mode.

## Layout norms
- Page wrapper centers content: `mx-auto max-w-2xl` (or `max-w-3xl`/`max-w-5xl`).
- Loading: render `SkeletonList`/`SkeletonCard` while data is `null`, then the content, then
  `EmptyState` if empty.

## File/naming conventions
- One page component per route in `src/pages/`, `PascalCase.jsx`, default export.
- Shared UI in `src/components/`; pure logic/exporters in `src/lib/`; data hooks in
  `src/hooks/`.
- Firestore collection names are `snake_case` (`weekly_forecasts`, `lesson_plans`,
  `quote_likes`).

## Tooling
- **yarn only** (never npm). `yarn dev`, `yarn build`, `yarn lint`, `yarn preview`.
- ESLint must stay clean (`yarn lint`) — flat config in `eslint.config.js`, with React Hooks
  + React Refresh rules. `dist` and `seed` are ignored.
- The React Compiler is on (Babel plugin) — don't hand-memoize reflexively.
