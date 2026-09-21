/**
 * The Firebase web config, as source — **the values a build always has**.
 *
 * These are public client identifiers, not secrets: Firebase's own documentation
 * says so, and Vite inlines them into the browser bundle either way. The security
 * boundary is `firestore.rules` plus the Authorized Domains list, not these six
 * strings.
 *
 * Why a committed module instead of only environment variables
 * -----------------------------------------------------------
 * `src/firebase.js` prefers a **non-blank** value from the build environment
 * (`VITE_FIREBASE_*`) and falls back to this file for anything the environment
 * does not supply. That ordering is the fix for a real deploy failure: the first
 * production build of this architecture had `.env.production` committed (a good
 * idea) and still shipped with no config, twice. What had happened:
 *
 *   * `Set-Content -Encoding utf8` on Windows PowerShell writes a **BOM**, and
 *     Vite's env parser does not strip it — the file yielded five values and
 *     silently dropped `VITE_FIREBASE_API_KEY`, whose line the BOM hugged. The
 *     build looked fine locally only because `.env.local` happened to supply
 *     that one key.
 *   * Vite's `loadEnv` lets `process.env` win: a variable that exists in the
 *     build environment but is *blank* shadows the file's value. So a half-typed
 *     Vercel variable can empty out a committed one with nothing to see.
 *
 * Reading the values from source removes both failure modes: no encoding, no
 * shadowing, no dashboard state. See `docs/gotchas.md` ("The way out").
 *
 * Editing these: they are per-project, so a new Firebase project means updating
 * this file. `src/firebaseConfig.test.js` checks the shape (all six present, the
 * project id matching `.firebaserc`, no BOM or stray whitespace) and
 * `dist/build-info.json` reports which source a given build used.
 */
export const firebaseConfig = {
  apiKey: 'AIzaSyAKBTQgJ_Ab5BVzMBpgOQF9c7quzNOnF9M',
  authDomain: 'beacon-edu-consult-proj.firebaseapp.com',
  projectId: 'beacon-edu-consult-proj',
  storageBucket: 'beacon-edu-consult-proj.firebasestorage.app',
  messagingSenderId: '928464195562',
  appId: '1:928464195562:web:8abfe4627dd19e32626c93',
}
