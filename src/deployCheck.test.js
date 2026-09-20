import { readFileSync } from 'node:fs'
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
    const fromPython = [...new Set([...python.matchAll(/get\(f"\{base\}(\/[^"]*)"/g)].map((m) => m[1]))].sort()
    expect(fromPython.length, 'the Python check found no paths — has it been rewritten?').toBeGreaterThanOrEqual(4)
    expect(declaredPaths()).toEqual(fromPython)
  })

  it('actually requests each declared path, not just declares it', () => {
    for (const path of declaredPaths()) {
      // The loop over the curriculum files goes through `get(path)`.
      const requested = node.includes(`get('${path}')`) || node.includes('get(path)')
      expect(requested, `verify_deploy.mjs declares ${path} but never requests it`).toBe(true)
    }
    // The two curriculum paths are the ones the loop walks, so it must exist.
    expect(node).toContain("CHECKED_PATHS.filter((p) => p.startsWith('/curriculum/'))")
  })

  it('tests both silent killers in both implementations', () => {
    for (const [name, source] of [['verify_deploy.py', python], ['verify_deploy.mjs', node]]) {
      expect(source, `${name} no longer checks firebaseConfigured`).toContain('firebaseConfigured')
      expect(source, `${name} no longer compares bundle hashes`).toContain('bundleHash')
      expect(source, `${name} no longer checks the catalog of deploy paths`).toMatch(/missingEnv/)
    }
  })

  it('reads the same six config values the app reads', () => {
    const fromVite = [...read('vite.config.js').matchAll(/'(VITE_FIREBASE_[A-Z_]+)'/g)].map((m) => m[1])
    const fromNode = [...node.matchAll(/'(VITE_FIREBASE_[A-Z_]+)'/g)].map((m) => m[1])
    expect(fromVite.length).toBe(6)
    expect([...new Set(fromNode)].sort()).toEqual([...new Set(fromVite)].sort())
    // And they must be the ones .env.example documents, or a fresh clone gets 1/6.
    for (const key of fromVite) expect(read('.env.example')).toContain(`${key}=`)
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
