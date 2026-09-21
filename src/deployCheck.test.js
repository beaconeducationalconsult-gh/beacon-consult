import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/*
 * Two things deploy checks get wrong, guarded here.
 *
 * 1. **Drift between the two implementations.** `scripts/verify_deploy.py` is
 *    what `make check` and CI run; `scripts/verify_deploy.mjs` is the same check
 *    for a Windows checkout, where Python may not be installed. Two copies of a
 *    checklist is one copy too many, so this compares them: both must probe the
 *    same deploy paths, and both must test the same two silent killers
 *    (a deploy built without Firebase config, and a deploy serving a curriculum
 *    this checkout does not).
 *
 * 2. **A Windows wrapper that stopped wrapping.** `scripts/deploy_check.ps1`
 *    exists so the person deploying does not have to remember Node's CLI. It
 *    must keep delegating to the .mjs — a PowerShell script that reimplements
 *    the checks is a third copy, untested, in the language least convenient to
 *    test.
 */

const ROOT = new URL('..', import.meta.url)
const read = (path) => readFileSync(new URL(path, ROOT), 'utf8').replace(/\r\n/g, '\n')

const python = read('scripts/verify_deploy.py')
const node = read('scripts/verify_deploy.mjs')
const powershell = read('scripts/deploy_check.ps1')

/** The deploy paths the Node script declares it checks. */
function declaredPaths() {
  const block = /const CHECKED_PATHS = \[([\s\S]*?)\]/.exec(node)
  expect(block, 'verify_deploy.mjs no longer declares CHECKED_PATHS').toBeTruthy()
  return [...block[1].matchAll(/'([^']+)'/g)].map((match) => match[1]).sort()
}

describe('the deploy checks agree with each other', () => {
  it('probes the same deploy paths in Python and in Node', () => {
    const block = /CHECKED_PATHS = \[([\s\S]*?)\n\]/.exec(python)
    expect(block, 'verify_deploy.py no longer declares CHECKED_PATHS').toBeTruthy()
    const fromPython = [...block[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]).sort()
    expect(fromPython.length, 'the Python declaration has shrunk').toBeGreaterThanOrEqual(4)
    expect(declaredPaths()).toEqual(fromPython)
  })

  it('actually requests each declared path, not just declares it', () => {
    // A path in the list that is never fetched is a check that silently stopped
    // happening. Each one has a named call site in both scripts.
    const usage = [
      ['/build-info.json', "get('/build-info.json')", 'get(f"{base}/build-info.json")'],
      ['/', "get('/')", 'get(f"{base}/")'],
      ['/sw.js', "get('/sw.js')", 'get(f"{base}/sw.js")'],
    ]
    for (const [path, nodeSnippet, pythonSnippet] of usage) {
      expect(declaredPaths()).toContain(path)
      expect(node, `verify_deploy.mjs declares ${path} but never requests it`).toContain(nodeSnippet)
      expect(python, `verify_deploy.py declares ${path} but never requests it`).toContain(pythonSnippet)
    }
    // The curriculum files are walked by the loop in both scripts.
    expect(node).toContain("CHECKED_PATHS.filter((p) => p.startsWith('/curriculum/'))")
    expect(python).toContain('[p for p in CHECKED_PATHS if p.startswith("/curriculum/")]')
  })

  it('compares the app\'s Firebase project with the one the CLI deploys to', () => {
    // Two files, two tools, one project: `.env.local` (Vite, gitignored) and
    // `.firebaserc` (the CLI, committed). `firebase deploy` follows .firebaserc,
    // so a mismatch publishes the rules to a project the app never talks to and
    // leaves the live one as it was.
    for (const [name, source] of [['verify_deploy.py', python], ['verify_deploy.mjs', node]]) {
      expect(source, `${name} no longer reads .firebaserc`).toContain('.firebaserc')
      expect(source, `${name} no longer compares project ids`).toMatch(/pinned.*!==|!==.*pinned|pinned != app_project/)
      expect(source, `${name} no longer names the fix`).toMatch(/firebase use/)
    }
  })

  it('reads a file the rewrite swallowed as the shell, not as a pass', () => {
    // The bug this guards: every path the deploy does not have answers 200 with
    // index.html, which used to count as a served file.
    for (const [name, source] of [['verify_deploy.mjs', node], ['verify_deploy.py', python]]) {
      expect(source, `${name} no longer detects the SPA shell`).toMatch(/looks[_A-Za-z]*[Ll]ike[Hh]tml|looks_like_html/)
      expect(source, `${name} no longer compares served sizes with this checkout`)
        .toMatch(/localFile|local_file/)
    }
  })

  it('tests both silent killers in both implementations', () => {
    for (const [name, source] of [['verify_deploy.py', python], ['verify_deploy.mjs', node]]) {
      expect(source, `${name} no longer checks firebaseConfigured`).toContain('firebaseConfigured')
      expect(source, `${name} no longer compares bundle hashes`).toContain('bundleHash')
      expect(source, `${name} no longer checks the catalog of deploy paths`).toMatch(/missingEnv/)
    }
  })

  it('reads the same six config values the app reads', () => {
    // `src/lib/firebaseConfigSource.js` is where the six names are written down —
    // the app, the build guard and the notice all read them from there — so the
    // pre-flight scripts are compared against it rather than against the list
    // that used to be duplicated in vite.config.js.
    const fromApp = [...read('src/lib/firebaseConfigSource.js').matchAll(/'(VITE_FIREBASE_[A-Z_]+)'/g)].map((m) => m[1])
    const fromNode = [...node.matchAll(/'(VITE_FIREBASE_[A-Z_]+)'/g)].map((m) => m[1])
    expect(fromApp.length).toBe(6)
    expect([...new Set(fromNode)].sort()).toEqual([...new Set(fromApp)].sort())
    // And they must be the ones .env.example documents, or a fresh clone gets 1/6.
    for (const key of fromApp) expect(read('.env.example')).toContain(`${key}=`)
  })

  it('does not build with a shell command only Unix has', () => {
    // `execSync('cat …')` here worked in a Linux container and silently set
    // bundleHash to null on the Windows machine that deploys — a build plugin
    // may only use Node APIs.
    // Comments are allowed to mention the pattern; only code counts.
    const vite = read('vite.config.js')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/\/\/[^\n]*/g, '')
    expect(vite).not.toMatch(/execSync\(\s*['"`](cat|ls|sed|grep|head)\b/)
    expect(vite).toContain("readFileSync(resolve(process.cwd(), 'public/curriculum/_BUILD_REPORT.json')")
  })

  it('keeps the Windows wrapper a wrapper', () => {
    expect(powershell).toContain('scripts/verify_deploy.mjs')
    expect(powershell).toContain('exit $LASTEXITCODE')
    // If this ever grows past a launcher, the checks have been copied into it.
    expect(powershell.split('\n').length).toBeLessThan(60)
    expect(powershell).not.toMatch(/build-info\.json\s*\)/) // no fetch/no JSON parsing of its own
  })

  it('leaves the Windows wrapper with nothing to do but hand over', () => {
    // The PowerShell file must not mention the deploy's URL shape or parse JSON.
    expect(powershell).not.toContain('ConvertFrom-Json')
    expect(powershell).not.toContain('Invoke-RestMethod')
  })
})


/*
 * The .env.local reader, end to end.
 *
 * A regression test for a bug that only appears on the machine that deploys.
 * Windows PowerShell writes `>` and `Out-File` as UTF-16LE, so a perfectly good
 * `.env.local` read as UTF-8 comes back full of NUL bytes, every key
 * "disappears", and the report says all six values are missing — on a machine
 * where the app runs fine. The check now decodes from the bytes and prints the
 * key *names* it found, which is what makes such a file self-explaining. It must
 * never print a value.
 */
describe('the .env.local reader understands what Windows writes', () => {
  const script = fileURLToPath(new URL('../scripts/verify_deploy.mjs', import.meta.url))
  const rootDir = fileURLToPath(new URL('..', import.meta.url))
  const KEYS = [
    'VITE_FIREBASE_API_KEY', 'VITE_FIREBASE_AUTH_DOMAIN', 'VITE_FIREBASE_PROJECT_ID',
    'VITE_FIREBASE_STORAGE_BUCKET', 'VITE_FIREBASE_MESSAGING_SENDER_ID', 'VITE_FIREBASE_APP_ID',
  ]
  const body = KEYS.map((key, index) => `${key}=value-${index}`).join('\n')

  /** Run the pre-flight's local half against a fixture and return everything it printed. */
  function run(fixture) {
    const dir = mkdtempSync(join(tmpdir(), 'beacon-env-'))
    const file = join(dir, '.env.local')
    writeFileSync(file, fixture)
    try {
      return execFileSync(process.execPath, [script, '-SkipBuild', '-EnvFile', file],
        { cwd: rootDir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
    } catch (error) {
      return `${error.stdout || ''}${error.stderr || ''}`
    }
  }

  it('reads a UTF-16LE file, BOM, `export` and quotes included', () => {
    const utf16 = Buffer.concat([
      Buffer.from([0xff, 0xfe]),
      Buffer.from(`export ${KEYS[0]}="value-0"\n${body.split('\n').slice(1).join('\n')}`, 'utf16le'),
    ])
    expect(run(utf16)).toContain('all six VITE_FIREBASE_* values are set')
  })

  it('reads a UTF-8 file with a byte-order mark', () => {
    expect(run(Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(body, 'utf8')])))
      .toContain('all six VITE_FIREBASE_* values are set')
  })

  it('names the keys it found when one is missing, and never the values', () => {
    // The project id is public (it ships in the client bundle and in the
    // committed .firebaserc), so it may appear; the other five must not.
    const partial = [
      'VITE_FIREBASE_API_KEY=pretend-secret',
      'VITE_FIREBASE_AUTH_DOMAIN=pretend-domain',
      'VITE_FIREBASE_PROJECT_ID=pretend-project',
    ].join('\n')
    const output = run(Buffer.from(partial, 'utf8'))
    expect(output).toContain('does not define: VITE_FIREBASE_STORAGE_BUCKET')
    expect(output).toContain('keys defined: VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID')
    expect(output).not.toContain('pretend-secret')
    expect(output).not.toContain('pretend-domain')
  })

  it('flags a project that is not the one .firebaserc deploys to', () => {
    const pinned = JSON.parse(readFileSync(new URL('../.firebaserc', import.meta.url), 'utf8'))
      .projects.default
    const elsewhere = KEYS.map((key) => `${key}=x`).join('\n')
      .replace('VITE_FIREBASE_PROJECT_ID=x', 'VITE_FIREBASE_PROJECT_ID=some-other-project')

    const mismatch = run(Buffer.from(elsewhere, 'utf8'))
    expect(mismatch).toContain('but the app is configured for `some-other-project`')
    expect(mismatch).toContain('would publish the rules and indexes to the project the app never talks to')
    expect(mismatch).toContain('firebase use some-other-project')

    // And silence when they agree — otherwise the check is just noise.
    const agreeing = Buffer.from(elsewhere.replace('some-other-project', pinned), 'utf8')
    const output = run(agreeing)
    expect(output).toContain(`.firebaserc pins the same project the app uses (${pinned})`)
    expect(output).not.toContain('would publish the rules and indexes')
  })

  it('tells "present but empty" apart from "not there at all"', () => {
    const output = run(Buffer.from(KEYS.map((key) => `${key}=`).join('\n'), 'utf8'))
    expect(output).toContain('set but empty')
    expect(output).not.toContain('does not define')
  })
})
