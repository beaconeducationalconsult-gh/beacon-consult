import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

/**
 * Invariants of `storage.rules` and of the client that talks to it (P3-3).
 *
 * Storage holds members' generated documents. The emulator is the right tool
 * for permission tests, but it needs a JVM (P2-1 in docs/TODO.md), so these are
 * the checks that run on every `make check`: they prove nobody quietly removed
 * a guard, and that the path the client builds is the path the rules allow.
 * They do not prove a rule is correct — read the rule when one fails.
 */

const ROOT = new URL('..', import.meta.url)
const source = readFileSync(new URL('storage.rules', ROOT), 'utf8')
const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '')
const code = stripComments(source)
const client = readFileSync(new URL('src/lib/generatedDocs.js', ROOT), 'utf8')

function block(pattern) {
  const re = new RegExp(`match\\s*\\/${pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{`)
  const m = re.exec(code)
  expect(m, `no match block for /${pattern}/ in storage.rules`).not.toBeNull()
  let depth = 0
  let i = m.index + m[0].length - 1
  const start = i
  for (; i < code.length; i += 1) {
    if (code[i] === '{') depth += 1
    else if (code[i] === '}') {
      depth -= 1
      if (depth === 0) break
    }
  }
  return code.slice(start, i + 1)
}

const generated = block('generated/{uid}/{file=**}')

/**
 * The `allow …` clause covering one operation. Operations may be combined
 * (`allow create, update: if …`), so the match is on the operation list.
 */
const clause = (op) => {
  const m = generated.match(new RegExp(`allow\\s+[^:]*\\b${op}\\b[^:]*:\\s*if([\\s\\S]*?);`))
  expect(m, `no allow ${op} clause for /generated/{uid}`).not.toBeNull()
  return m[1]
}

describe('the generated-documents folder is private to its owner', () => {
  it('reads require the owner or an admin', () => {
    const read = clause('read')
    expect(read).toContain('request.auth.uid == uid')
    expect(read).toContain('isAdmin()')
    expect(read).toContain('isSignedIn()')
  })

  it('writes require an approved member writing under their own uid', () => {
    const write = [clause('create'), clause('update')].join('\n')
    expect(write).toContain('isApprovedOrAdmin()')
    expect(write).toContain('request.auth.uid == uid')
  })

  it('caps the size of an upload, in the rule and not only in the client', () => {
    const write = [clause('create'), clause('update')].join('\n')
    expect(write).toMatch(/request\.resource\.size\s*<=\s*8\s*\*\s*1024\s*\*\s*1024/)
    const clientLimit = client.match(/MAX_UPLOAD_BYTES\s*=\s*(\d+)\s*\*\s*(\d+)\s*\*\s*(\d+)/)
    expect(clientLimit, 'MAX_UPLOAD_BYTES missing from generatedDocs.js').not.toBeNull()
    expect(Number(clientLimit[1]) * Number(clientLimit[2]) * Number(clientLimit[3])).toBe(8 * 1024 * 1024)
  })

  it('denies everything outside that folder', () => {
    expect(block('{allPaths=**}')).toMatch(/allow\s+read\s*,\s*write\s*:\s*if\s+false/)
  })

  it('never grants unconditional access anywhere in the file', () => {
    expect(code).not.toMatch(/if\s+true\s*[;)]/)
    expect(code).not.toMatch(/allow\s+\w+\s*:\s*if\s*;/)
    expect(source).toContain("rules_version = '2';")
  })
})

describe('the client and the rules agree on the path', () => {
  it('builds paths under `generated/{uid}/`, the one shape the rules allow', () => {
    expect(client).toMatch(/`generated\/\$\{uid\}\//)
  })

  it('is wired into firebase.json so the CLI deploys it', () => {
    const config = JSON.parse(readFileSync(new URL('firebase.json', ROOT), 'utf8'))
    expect(config.storage?.rules).toBe('storage.rules')
  })

  it('is named in the deploy docs, because deploying is a separate step', () => {
    const docs = readFileSync(new URL('docs/security.md', ROOT), 'utf8')
    expect(docs).toContain('storage.rules')
    expect(docs).toContain('firebase deploy --only storage')
  })
})
