import { FIREBASE_ENV_BLOCK } from './firebaseConfigSource'

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
        'Fill them into the committed config — src/firebaseConfig.js, one line per value. This is ' +
        'the source every build can read, so it needs no dashboard step:',
      code: 'src/firebaseConfig.js\n  apiKey: …\n  projectId: …',
    },
    {
      title:
        'Or set them in the build environment instead: Vercel → the project whose Domains tab ' +
        'lists this address → Settings → Environment Variables. All six names, spelled exactly ' +
        'as below, each with a value, each enabled for Production (tick Preview as well):',
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
      'This deployed build was compiled without any of the six VITE_FIREBASE_* values. Vite ' +
      'inlines them when the build runs, and a build takes them from two places: the build ' +
      'environment (Vercel → Settings → Environment Variables) and the committed ' +
      'src/firebaseConfig.js. Both were empty for this build — a .env.local on a laptop is not ' +
      'part of a deploy. (Working locally instead? The same six values go in .env.local.)',
    steps,
    missing,
    note:
      'Keep the VITE_ prefix if you use the environment: Vite exposes build-time values only under ' +
      'that name. These are public client identifiers — they ship inside the bundle either way — so ' +
      'Vercel\'s "keep this value private" prompt is optional. An environment value that is empty ' +
      'counts as absent and falls back to the committed file.',
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
    {
      title:
        'Or fill them into src/firebaseConfig.js, the committed config every build falls back to ' +
        '(a blank value there is the same as no value):',
      code: null,
    },
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
