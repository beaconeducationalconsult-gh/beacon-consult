#!/usr/bin/env node
/*
 * verify_deploy.mjs — the pre-flight for a deploy, from a Windows or any other
 * checkout, with nothing but Node (which a checkout already has).
 *
 * `scripts/verify_deploy.py` is its peer: same checks, same exit code, run by
 * `make check` and by Unix CI. This one exists because the machine that
 * *deploys* is Windows and PowerShell is the shell there — and because the
 * checks that matter most are about a deployment's own settings, which nothing
 * else in the pipeline can see.
 *
 *   node scripts/verify_deploy.mjs                          # the local half
 *   node scripts/verify_deploy.mjs -Url https://beacon.vercel.app
 *   node scripts/verify_deploy.mjs -Url https://… -SkipBuild
 *
 * What it proves, in the order the answers matter:
 *
 *   1. the checkout is what will be built  (branch, HEAD, uncommitted work)
 *   2. the local Firebase config is complete (.env.local, six VITE_FIREBASE_*)
 *   3. a build carries it                  (dist/build-info.json)
 *   4. **the deploy** has it               (GET /build-info.json — Vercel has its
 *                                           own variables; a green local build
 *                                           says nothing about the deployed one)
 *   5. the deploy serves this checkout's curriculum, on the commit you think
 *      it does, with the rewrites working
 *
 * It never prints the values from .env.local, only which of them are present.
 * Exit code 1 if anything a teacher would hit is wrong.
 */
import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const FIREBASE_KEYS = [
  'VITE_FIREBASE_API_KEY',
  'VITE_FIREBASE_AUTH_DOMAIN',
  'VITE_FIREBASE_PROJECT_ID',
  'VITE_FIREBASE_STORAGE_BUCKET',
  'VITE_FIREBASE_MESSAGING_SENDER_ID',
  'VITE_FIREBASE_APP_ID',
]
/* Every deploy path this checks. `src/deployCheck.test.js` compares this list against
 * verify_deploy.py's, so the two implementations cannot drift apart. */
const CHECKED_PATHS = [
  '/build-info.json',
  '/',
  '/curriculum/grades.json',
  '/curriculum/schedules/b1-mathematics.json',
  '/sw.js',
]

const args = process.argv.slice(2)
const flag = (name) => args.includes(name)
const value = (name) => {
  const withEquals = args.find((a) => a.startsWith(`${name}=`))
  if (withEquals) return withEquals.slice(name.length + 1)
  const at = args.indexOf(name)
  return at >= 0 ? args[at + 1] : undefined
}

const URL_ARG = value('-Url') || value('--url') || args.find((a) => /^https?:\/\//.test(a))
const SKIP_BUILD = flag('-SkipBuild') || flag('--skip-build')

/* Step numbering follows what actually ran: -SkipBuild drops step 3. */
let laterStep = 4
const problems = []
const ok = (message) => console.log(`  ok  ${message}`)
const bad = (message) => { problems.push(message); console.log(`  x   ${message}`) }
const warn = (message) => console.log(`  !   ${message}`)
const step = (message) => console.log(`\n${message}`)

/* ── 1. the checkout ─────────────────────────────────────────────────────── */
step('1. The checkout')
try {
  const git = (...a) => execFileSync('git', a, { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
  ok(`on ${git('rev-parse', '--abbrev-ref', 'HEAD')} at ${git('rev-parse', '--short', 'HEAD')}`)
  const dirty = git('status', '--porcelain').split('\n').filter(Boolean)
  if (dirty.length) {
    warn(`${dirty.length} uncommitted file(s) — Vercel builds the pushed commit, not your working tree, so none of this will be in the deploy`)
  }
} catch {
  warn('not a git checkout — cannot tell which commit is being deployed')
}

/* ── 2. the local Firebase config ────────────────────────────────────────── */
step('2. The local Firebase config (.env.local)')
const envPath = join(ROOT, '.env.local')
const env = {}
if (!existsSync(envPath)) {
  bad('.env.local is missing — copy .env.example to .env.local and fill in the six values from the Firebase console (Project settings → Your apps → Web app)')
} else {
  for (const line of readFileSync(envPath, 'utf8').split('\n')) {
    const match = /^\s*([A-Z0-9_]+)\s*=\s*(.*)$/.exec(line)
    if (match) env[match[1]] = match[2].trim()
  }
  const missing = FIREBASE_KEYS.filter((key) => !env[key])
  if (missing.length) bad(`.env.local is missing: ${missing.join(', ')}`)
  else ok(`all six VITE_FIREBASE_* values are set (project ${env.VITE_FIREBASE_PROJECT_ID})`)
}

/* ── 3. a local build carries it ─────────────────────────────────────────── */
let local = null
if (!SKIP_BUILD) {
  step('3. A local build carries it')
  const yarn = spawnSync('yarn', ['build'], { cwd: ROOT, stdio: 'inherit', shell: process.platform === 'win32' })
  if (yarn.error || yarn.status !== 0) bad(`the build failed (${yarn.error?.message || `exit ${yarn.status}`}) — run \`yarn build\` on its own to see why`)
}
const infoPath = join(ROOT, 'dist', 'build-info.json')
if (existsSync(infoPath)) {
  local = JSON.parse(readFileSync(infoPath, 'utf8'))
  if (local.firebaseConfigured) {
    ok(`the build embedded the Firebase config (bundle ${local.bundleHash}, commit ${local.commit})`)
  } else {
    bad(`the build was made WITHOUT Firebase config (missing: ${(local.missingEnv || []).join(', ')}) — the deployed app would show the setup notice, not the portal`)
  }
  laterStep = 4
} else if (SKIP_BUILD) {
  laterStep = 3
  warn('dist/build-info.json is absent — run without -SkipBuild to check what a build carries')
} else {
  bad('dist/build-info.json was not written — the build did not complete')
}

/* ── 4 & 5. the deployment itself ────────────────────────────────────────── */
if (!URL_ARG) {
  step(`${laterStep}. The rules and indexes this project needs`)
  console.log('      Publishing them is a separate step — they are not part of the Vercel build:')
  console.log('        make deploy-rules      # firestore.rules + firestore.indexes.json')
  console.log('        make deploy-storage    # storage.rules (the document library)')
  console.log('      Then re-run this script with -Url to check the deployment itself.')
} else {
  const base = URL_ARG.replace(/\/+$/, '')
  step(`${laterStep}. The deployment at ${base}`)
  const get = async (path) => {
    const response = await fetch(`${base}${path}`, { redirect: 'follow', signal: AbortSignal.timeout(25_000) })
    return { status: response.status, body: await response.text() }
  }

  try {
    const { status, body } = await get('/build-info.json')
    if (status !== 200) {
      bad(`GET /build-info.json → ${status} (the deploy predates this check, or a rewrite swallows it)`)
    } else {
      const remote = JSON.parse(body)
      if (remote.firebaseConfigured) {
        ok(`the deploy has its Firebase config (project ${remote.projectId}, commit ${remote.commit}, built ${remote.builtAt})`)
      } else {
        bad(`the deploy was built WITHOUT Firebase config (missing: ${(remote.missingEnv || []).join(', ')}) — set all six VITE_FIREBASE_* values in Vercel → Settings → Environment Variables for BOTH Production and Preview, then redeploy`)
      }
      if (remote.bundleHash && local?.bundleHash && remote.bundleHash !== local.bundleHash) {
        bad(`the deploy serves curriculum ${remote.bundleHash} but this checkout builds ${local.bundleHash} — the curriculum changed since the last deploy`)
      } else if (remote.bundleHash) {
        ok(`serving the curriculum this checkout builds (${remote.bundleHash})`)
      }
      if (local?.commit && remote.commit && remote.commit !== local.commit) {
        warn(`the deploy is commit ${remote.commit}; this checkout's build is ${local.commit} — if you just pushed, wait for Vercel, then re-run`)
      }
    }
  } catch (error) {
    bad(`GET /build-info.json failed (${error.message})`)
  }

  try {
    const { status, body } = await get('/')
    if (status === 200 && body.includes('id="root"')) ok('the SPA shell is served')
    else bad(`GET / → ${status}; the app shell did not come back (a broken rewrite makes every deep link 404)`)
  } catch (error) {
    bad(`GET / failed (${error.message})`)
  }

  for (const path of CHECKED_PATHS.filter((p) => p.startsWith('/curriculum/'))) {
    try {
      const { status, body } = await get(path)
      if (status !== 200) bad(`GET ${path} → ${status} — the curriculum bundle is not deployed, so grade and subject dropdowns come up empty`)
      else if (path.endsWith('grades.json')) {
        try { ok(`${path} is served (${JSON.parse(body).length} grades)`) } catch { bad(`${path} did not return JSON`) }
      } else ok(`${path} is served (${Math.round(body.length / 1024)} KB)`)
    } catch (error) {
      bad(`GET ${path} failed (${error.message})`)
    }
  }

  try {
    const { status, body } = await get('/sw.js')
    if (status !== 200) bad(`GET /sw.js → ${status} — offline mode would never install`)
    else if (!body.includes('bundleHash')) bad('the deployed sw.js does not read the bundle hash — it is an older build, and returning browsers would keep a stale cache')
    else ok('sw.js reads the bundle hash (offline installs pick up new data)')
  } catch (error) {
    bad(`GET /sw.js failed (${error.message})`)
  }
}

console.log()
if (problems.length) {
  console.log(`${problems.length} problem(s) — the deployed app would not work for a teacher.`)
  process.exit(1)
}
console.log('Deploy looks right.')
if (URL_ARG) console.log('Now drive the flows by hand: docs/verification.md has the checklist (it needs a signed-in account).')
else console.log('Re-run with -Url https://your-deploy to check the deployment itself.')
