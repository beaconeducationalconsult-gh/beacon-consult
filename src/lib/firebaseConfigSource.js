/**
 * Where the six Firebase web-config values come from, and how a build decides
 * between the build environment and the committed file.
 *
 * The names are written down exactly once, here: `src/firebase.js` reads them
 * from the environment, `src/firebaseConfig.js` supplies the committed
 * fallbacks, and `SetupNotice.jsx` prints whichever are missing. A test asserts
 * the three agree with `.env.example`.
 *
 * The rule for a value, in `resolveFirebaseConfig`:
 *
 *   * an environment value that is **non-blank** wins — so an operator can point
 *     a deploy at a different Firebase project without touching the repository;
 *   * anything blank or absent falls back to the committed value;
 *   * a variable that exists in the environment but is *blank* is reported
 *     (`envBlankNames`), because it is invisible otherwise: Vite makes
 *     `process.env` win over `.env` files, so one empty dashboard variable used
 *     to empty out a committed value and leave the deployed app showing the
 *     setup notice with a green build. That is exactly what the second real
 *     deploy of this architecture did.
 */

/** The six values, keyed by the name the app uses, valued by the env var name. */
export const FIREBASE_ENV_NAMES = {
  apiKey: 'VITE_FIREBASE_API_KEY',
  authDomain: 'VITE_FIREBASE_AUTH_DOMAIN',
  projectId: 'VITE_FIREBASE_PROJECT_ID',
  storageBucket: 'VITE_FIREBASE_STORAGE_BUCKET',
  messagingSenderId: 'VITE_FIREBASE_MESSAGING_SENDER_ID',
  appId: 'VITE_FIREBASE_APP_ID',
}

/** The same six, in the order `.env.example` lists them. */
export const FIREBASE_ENV_LIST = Object.values(FIREBASE_ENV_NAMES)

/** The six lines as they appear in `.env.example`, for the paste instructions. */
export const FIREBASE_ENV_BLOCK = FIREBASE_ENV_LIST.map((name) => `${name}=…`).join('\n')

/** Blank-by-any-definition: undefined, null, empty, or spaces only. */
const blank = (value) => String(value ?? '').trim() === ''

/**
 * Which of the six a config is missing, as env var names — what the setup notice
 * prints so the reader does not have to guess which one is empty.
 *
 * An empty string counts as missing; that is the shape a Vercel variable with no
 * value produces, and the shape `.env.example` has before it is filled in.
 */
export function missingEnvNames(config = {}) {
  return Object.keys(FIREBASE_ENV_NAMES)
    .filter((key) => blank(config[key]))
    .map((key) => FIREBASE_ENV_NAMES[key])
}

/**
 * The config a build (and the running app) actually uses, from both sources.
 *
 * Returns `{ config, missing, source, fromEnv, fromCommitted, envBlankNames }`:
 * the merged six values; the env names still missing; which side the values came
 * from; and the names that exist in the environment but are blank — the ones
 * worth naming in a build log, because they are the ones that used to fail
 * silently.
 */
export function resolveFirebaseConfig({ env = {}, committed = {} } = {}) {
  const config = {}
  const fromEnv = []
  const fromCommitted = []
  const envBlankNames = []

  for (const [key, name] of Object.entries(FIREBASE_ENV_NAMES)) {
    const envValue = String(env[name] ?? '').trim()
    const committedValue = String(committed[key] ?? '').trim()

    // The variable is there but empty: Vite lets `process.env` win over `.env`
    // files, so before the fallback existed this silently emptied a value the
    // repository had supplied. Worth naming in a build log, because the
    // dashboard shows the variable as if it were configured.
    if (!envValue && env[name] !== undefined) envBlankNames.push(name)

    if (envValue) {
      config[key] = envValue
      fromEnv.push(key)
    } else if (committedValue) {
      config[key] = committedValue
      fromCommitted.push(key)
    } else {
      config[key] = ''
    }
  }

  const source = fromEnv.length === 0 ? 'committed' : fromCommitted.length === 0 ? 'env' : 'mixed'

  return {
    config,
    missing: missingEnvNames(config),
    source,
    fromEnv: fromEnv.map((key) => FIREBASE_ENV_NAMES[key]),
    fromCommitted: fromCommitted.map((key) => FIREBASE_ENV_NAMES[key]),
    envBlankNames,
  }
}
