/**
 * The copy behind `src/components/SetupNotice.jsx` — the screen a build shows
 * when the six `VITE_FIREBASE_*` values were not there when it was compiled.
 *
 * Two readers, two fixes, and they are not interchangeable:
 *
 *   * on a laptop the values live in `.env.local`, and the dev server has to be
 *     restarted, because Vite reads env files only at startup;
 *   * on a deploy there is **no file to edit**. Whatever the build saw is what
 *     got inlined into the bundle, so the values have to exist in the build's
 *     own environment (Vercel → Settings → Environment Variables) and the build
 *     has to run again — Vercel does not rebuild because a variable changed.
 *
 * Until 2026-09-20 the screen showed the laptop instructions to everybody. The
 * first real deploy was built without the six values, and the person staring at
 * the live URL was told to copy a file that exists nowhere near that problem.
 * The same failure now also names itself over HTTP, with nothing to click:
 * `GET /build-info.json` on the deploy (`firebaseConfigured`, `missingEnv`).
 */

/**
 * The six values the app needs, keyed by the name it uses inside the app.
 *
 * This is the one place the pairs are written down. `firebase.js` reads the
 * values (its `import.meta.env.VITE_FIREBASE_*` reads must stay literal for
 * Vite's build-time replacement) and passes the result to `missingEnvNames`,
 * so the list of names here cannot drift from the config it describes.
 */
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

/**
 * Which of the six a config is missing, as env var names.
 *
 * An empty string counts as missing — that is the shape a Vercel variable with
 * no value produces, and the shape `.env.example` has before it is filled in.
 * `VITE_FIREBASE_STORAGE_BUCKET` is the one exception in practice: leaving it
 * empty is a supported state (a project with no Cloud Storage bucket), so it
 * never on its own makes `firebaseConfigured` false — see `firebase.js`.
 */
export function missingEnvNames(config = {}) {
  return Object.keys(FIREBASE_ENV_NAMES)
    .filter((key) => !String(config[key] ?? '').trim())
    .map((key) => FIREBASE_ENV_NAMES[key])
}

/**
 * Is this hostname the machine the build was made on?
 *
 * `import.meta.env.PROD` alone is not enough: `yarn build && yarn preview` runs
 * the production bundle on localhost, and telling that reader to go and edit
 * Vercel settings would be the old mistake in the other direction.
 */
export function isLocalHost(hostname = '') {
  const host = String(hostname).trim().toLowerCase().replace(/^\[|\]$/g, '')
  return (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host === '::1' ||
    host === '0.0.0.0' ||
    host.endsWith('.localhost') ||
    // A cloud dev sandbox (Arena, and the same shape as `vite.config.js`'s
    // allowedHosts entry) serves `yarn build`/`yarn preview` over a generated
    // hostname. It is a production *build*, but the reader still has the
    // repository in front of them, so the laptop instructions are the useful
    // ones — the deploy copy would send them to Vercel for no reason.
    host.endsWith('.e2b.app')
  )
}

/** `'deploy'` for a real deployment, `'local'` for a dev server or a preview build. */
export function setupNoticeMode({ prod, hostname } = {}) {
  return prod && !isLocalHost(hostname) ? 'deploy' : 'local'
}

/** The URL whose body answers "did this build have the values?" */
export function buildInfoUrl(origin = '') {
  return `${String(origin).replace(/\/+$/, '')}/build-info.json`
}

const CURRICULUM_CARD = {
  title: 'Nothing is wrong with the curriculum data',
  body:
    'Grades, subjects, indicators and schedules are committed as static JSON in public/curriculum/ ' +
    '(44 files, 11 grades, 4,040 indicators). They need no build step to be served — the Python ' +
    'scripts only regenerate them from the NaCCA sources when the data itself changes.',
}

function deployCopy({ missing, origin }) {
  const steps = [
    {
      title:
        'In Vercel, open the project → Settings → Environment Variables. All six names must be ' +
        'there, spelled exactly as below, each with a value, and each one enabled for ' +
        'Production (tick Preview as well):',
      code: FIREBASE_ENV_BLOCK,
    },
  ]

  if (missing.length) {
    steps.push({
      title: `This build was compiled without:`,
      code: missing.join('\n'),
    })
  }

  steps.push({
    title:
      'Redeploy. Adding or editing a variable does not rebuild anything by itself: Deployments → ' +
      '⋯ → Redeploy (or push any commit). Leave "Use existing Build Cache" unchecked if the old ' +
      'build is still being served.',
  })

  steps.push({
    title:
      'Check the build itself, without opening the app — this must answer ' +
      '"firebaseConfigured": true, with the project id you expect:',
    code: buildInfoUrl(origin),
  })

  return {
    mode: 'deploy',
    lead:
      'This deployed build was compiled without any of the six VITE_FIREBASE_* values — Vite ' +
      'inlines them when the build runs, so they have to live in the build environment. A ' +
      '.env.local on a laptop is not part of a deploy, which is why this build has no project to ' +
      'talk to. (Working locally instead? The same six values go in .env.local.)',
    steps,
    missing,
    note:
      'Keep the VITE_ prefix: Vite exposes build-time values only under that name. These are public ' +
      'client identifiers — they ship inside the bundle either way — so Vercel\'s "keep this value ' +
      'private" prompt is optional.',
    curriculum: CURRICULUM_CARD,
    footnote:
      'See docs/build-deploy.md (step 5) for the console walkthrough, and docs/gotchas.md ("Env ' +
      'vars are required at build time") for how a deploy can be green without them.',
  }
}

function localCopy({ missing }) {
  const steps = [
    { title: 'Copy the example file:', code: 'cp .env.example .env.local' },
    {
      title: 'Paste the values from the Firebase console → Project settings → Your apps → Web app:',
      code: FIREBASE_ENV_BLOCK,
    },
    { title: 'Restart the dev server — Vite reads env files only at startup:', code: 'yarn dev' },
  ]

  return {
    mode: 'local',
    lead:
      'The app can read the NaCCA curriculum offline, but signing in and saving work go through ' +
      'Firebase. Vite embeds the VITE_FIREBASE_* values at build time, and none were found — so ' +
      'this build has no project to talk to.',
    steps,
    missing,
    note: null,
    curriculum: CURRICULUM_CARD,
    footnote:
      'See docs/build-deploy.md for the full setup, and docs/gotchas.md for this failure mode.',
  }
}

/**
 * Everything `SetupNotice.jsx` renders, as plain data so it can be asserted
 * without a DOM.
 */
export function setupNoticeCopy({ mode = 'local', missing = [], origin = '' } = {}) {
  const copy = mode === 'deploy' ? deployCopy({ missing, origin }) : localCopy({ missing })
  return { title: 'Firebase configuration is missing', ...copy }
}
