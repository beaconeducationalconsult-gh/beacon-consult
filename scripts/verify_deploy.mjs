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
 *   node scripts/verify_deploy.mjs -EnvFile other.env        # read another env file
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
import { basename, dirname, join, resolve } from 'node:path'

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

/**
 * What the same file looks like in this checkout.
 *
 * Comparing the served bytes with the local ones is the check that catches the
 * deployment nobody suspects: the production domain serving a **different
 * branch** than the one that was pushed. It answers 200, the shell renders, and
 * every file that exists in both branches looks fine — while anything added
 * since answers with the SPA shell instead of the file, which reads as "ok, 2
 * KB" if all you look at is the status code.
 */
function localFile(urlPath) {
  const file = join(ROOT, 'public', urlPath.replace(/^\//, ''))
  if (!existsSync(file)) return null
  const bytes = readFileSync(file)
  let json = null
  try {
    json = JSON.parse(bytes.toString('utf8'))
  } catch {
    json = null
  }
  return { bytes: bytes.length, json }
}

/** Does this 200 look like the SPA shell rather than the file that was asked for? */
const looksLikeHtml = (body) => /^\s*(<!doctype|<html)/i.test(body)

const kb = (bytes) => `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`

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
/**
 * Read a dotenv file the way the file actually is on Windows.
 *
 * `readFileSync(path, 'utf8')` was wrong, and wrong in the most annoying way:
 * Windows PowerShell writes `>` and `Out-File` as **UTF-16LE**, so a perfectly
 * good `.env.local` came back as a string full of NUL bytes, not one key
 * matched, and the report said all six values were missing on a machine where
 * the app runs fine. Decode from the bytes (BOM first, then a NUL-byte sniff),
 * accept `export KEY=…`, strip the quotes both shells add, and report the key
 * *names* it found — never the values — so a mismatch explains itself.
 */
function readEnvFile(path) {
  const bytes = readFileSync(path)
  let text
  let encoding = 'UTF-8'
  const evenLength = bytes.length % 2 === 0
  if (bytes[0] === 0xff && bytes[1] === 0xfe) {
    text = bytes.subarray(2).toString('utf16le')
    encoding = 'UTF-16LE'
  } else if (bytes[0] === 0xfe && bytes[1] === 0xff && evenLength) {
    text = Buffer.from(bytes).swap16().toString('utf16le')
    encoding = 'UTF-16BE'
  } else {
    text = bytes.toString('utf8')
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1)
    // No BOM, but every other byte is NUL: PowerShell again.
    if (evenLength && /\u0000/.test(text.slice(0, 400))) {
      text = bytes.toString('utf16le')
      encoding = 'UTF-16LE (no byte-order mark)'
    }
  }

  const env = {}
  const lines = text.split(/\r?\n/)
  for (const raw of lines) {
    const line = raw.trim()
    if (!line || line.startsWith('#')) continue
    const match = /^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line)
    if (!match) continue
    let value = match[2].trim()
    if (value.length > 1
      && ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))) {
      value = value.slice(1, -1)
    }
    env[match[1]] = value
  }
  return { env, encoding, lines: lines.filter((line) => line.trim()).length }
}

step('2. The local Firebase config (.env.local)')
// `-EnvFile` exists so the reader can be pointed at a fixture; the deploy
// machine always wants the default.
const envPath = value('-EnvFile') || value('--env-file') || join(ROOT, '.env.local')
const env = {}
if (!existsSync(envPath)) {
  bad('.env.local is missing — copy .env.example to .env.local and fill in the six values from the Firebase console (Project settings → Your apps → Web app)')
} else {
  const parsed = readEnvFile(envPath)
  const { encoding, lines } = parsed
  Object.assign(env, parsed.env)
  const present = FIREBASE_KEYS.filter((key) => key in env)
  const blank = present.filter((key) => !env[key])
  const missing = FIREBASE_KEYS.filter((key) => !(key in env))
  if (missing.length || blank.length) {
    const label = basename(envPath)
    bad(missing.length
      ? `${label} does not define: ${missing.join(', ')}`
      : `${blank.join(', ')} in ${label} ${blank.length > 1 ? 'are' : 'is'} set but empty`)
    // The diagnostic that makes this self-explaining: what the file really says.
    warn(`read as ${encoding}; ${lines} non-blank line(s); keys defined: ${Object.keys(env).join(', ') || 'none'}`)
    warn('Vite only reads names starting VITE_ that are listed in .env.example')
  } else {
    ok(`all six VITE_FIREBASE_* values are set (project ${env.VITE_FIREBASE_PROJECT_ID})`)
  }
}

/*
 * The app and the rules have to live in the same Firebase project.
 *
 * They are configured in two different files — `.env.local` (Vite, gitignored)
 * and `.firebaserc` (the Firebase CLI, committed) — and nothing used to compare
 * them. `make deploy-rules` runs `firebase deploy` with no `--project`, so it
 * follows `.firebaserc`: point that at one project while the app talks to
 * another and every publish is a no-op on the project that matters, while the
 * live one keeps whatever rules it has — an open test-mode database, if the
 * project is new.
 */
const projectInPlay = env.VITE_FIREBASE_PROJECT_ID
let pinnedProject = null
try {
  pinnedProject = JSON.parse(readFileSync(join(ROOT, '.firebaserc'), 'utf8'))?.projects?.default || null
} catch {
  pinnedProject = null
}
if (!pinnedProject) {
  warn('.firebaserc has no default project — `firebase deploy` will ask, or needs --project')
} else if (projectInPlay && pinnedProject !== projectInPlay) {
  bad(`.firebaserc pins \`${pinnedProject}\` but the app is configured for \`${projectInPlay}\` — `
    + '`firebase deploy` (and `make deploy-rules`) would publish the rules and indexes to the '
    + 'project the app never talks to, leaving the live one on whatever rules it has')
  warn(`fix: run \`firebase use ${projectInPlay}\` (writes .firebaserc), or commit the change, `
    + `or deploy with \`--project ${projectInPlay}\``)
} else if (projectInPlay) {
  ok(`.firebaserc pins the same project the app uses (${pinnedProject})`)
}

/* ── 3. a local build carries it ─────────────────────────────────────────── */
let local = null
if (!SKIP_BUILD) {
  step('3. A local build carries it')
  // The build is run through Vite's own entry point rather than through a package
  // manager: `vite build` is exactly what the `build` script runs, and it makes
  // this check independent of which Yarn a machine has on PATH (a global Yarn 1
  // refuses to run a repo whose packageManager is Yarn 4, which reads as a
  // failure of the deploy when it is a failure of the shell).
  const vite = join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js')
  const build = existsSync(vite)
    ? spawnSync(process.execPath, [vite, 'build'], { cwd: ROOT, stdio: 'inherit' })
    : spawnSync('yarn', ['build'], { cwd: ROOT, stdio: 'inherit', shell: process.platform === 'win32' })
  if (!existsSync(vite)) warn('node_modules/vite is missing — fell back to `yarn build`; run `yarn install` if this fails')
  if (build.error || build.status !== 0) bad(`the build failed (${build.error?.message || `exit ${build.status}`}) — run \`yarn build\` on its own to see why`)
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
    } else if (looksLikeHtml(body)) {
      bad('GET /build-info.json returned the SPA shell — this deploy was built before build-info.json existed, so it is **not** the commit you pushed. On Vercel, check Settings → Git → Production Branch: production deploys `main` unless you change it, and `main` is still the old snapshot')
    } else {
      const remote = JSON.parse(body)
      if (remote.firebaseConfigured) {
        ok(`the deploy has its Firebase config (project ${remote.projectId}, commit ${remote.commit}, built ${remote.builtAt})`)
      } else {
        bad(`the deploy was built WITHOUT Firebase config (missing: ${(remote.missingEnv || []).join(', ')}) — set all six VITE_FIREBASE_* values in Vercel → Settings → Environment Variables for BOTH Production and Preview, then redeploy`)
      }
      if (remote.projectId && projectInPlay && remote.projectId !== projectInPlay) {
        bad(`the deploy was built for project \`${remote.projectId}\`, but this checkout's .env.local `
          + `configures \`${projectInPlay}\` — the deployment and your local app are talking to `
          + 'different Firebase projects')
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

  let shellForMissingFile = false
  for (const path of CHECKED_PATHS.filter((p) => p.startsWith('/curriculum/'))) {
    const local = localFile(path)
    try {
      const { status, body } = await get(path)
      if (status !== 200) {
        bad(`GET ${path} → ${status} — the curriculum bundle is not deployed, so grade and subject dropdowns come up empty`)
        continue
      }
      if (looksLikeHtml(body)) {
        // A 200 that is the app shell: the rewrite caught a path the deploy does
        // not have. This is the signature of the wrong (older) branch.
        shellForMissingFile = true
        bad(`GET ${path} returned the SPA shell, not the file — this deploy does not contain ${path}${local ? ` (this checkout has it, ${kb(local.bytes)})` : ''}`)
        continue
      }
      let served = null
      try { served = JSON.parse(body) } catch { served = null }
      if (served === null) {
        bad(`GET ${path} did not return JSON — the file is not what the app expects`)
      } else if (!local) {
        ok(`${path} is served (${kb(Buffer.byteLength(body))}) — no local copy to compare`)
      } else if (Array.isArray(served) && Array.isArray(local.json) && served.length !== local.json.length) {
        bad(`${path} holds ${served.length} entries; this checkout's copy holds ${local.json.length} — the deploy is serving a different curriculum than this checkout`)
      } else {
        const servedBytes = Buffer.byteLength(body)
        const drift = Math.abs(servedBytes - local.bytes) / local.bytes
        if (drift > 0.10) {
          bad(`${path} is ${kb(servedBytes)} on the deploy but ${kb(local.bytes)} in this checkout (${Math.round(drift * 100)}% different) — the deploy is serving a different curriculum than this checkout`)
        } else {
          ok(`${path} matches this checkout (${kb(servedBytes)}${Array.isArray(served) ? `, ${served.length} entries` : ''})`)
        }
      }
    } catch (error) {
      bad(`GET ${path} failed (${error.message})`)
    }
  }
  if (shellForMissingFile) {
    warn('a curriculum file coming back as the app shell means the rewrite served index.html — almost always the wrong branch: Vercel deploys the Production Branch to this domain (main by default), not the branch you pushed')
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
