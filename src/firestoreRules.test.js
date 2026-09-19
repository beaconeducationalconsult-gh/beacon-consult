import { readFileSync, readdirSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

/**
 * Invariants of `firestore.rules`, checked without the emulator.
 *
 * The rules are the only thing between the database and the public internet,
 * and the review that adopted them found a critical hole: `allow create` on
 * `users` did not constrain the document, so any signup could write itself
 * `status:'approved'` and walk past every other rule. The emulator is the right
 * tool for permission tests (P2-1 in docs/TODO.md) but it needs a JVM, so these
 * are the checks that run on every `make check` and in CI.
 *
 * They parse the rules file and the client source. They do not prove a rule is
 * correct — they prove nobody quietly removed a guard. When one fails, read the
 * message: it names the collection and what went missing.
 */

const ROOT = new URL('..', import.meta.url)

/*
 * Line endings are normalized on read, and that is not cosmetic.
 *
 * A Windows checkout (git's `core.autocrlf`, which is on by default in Git for
 * Windows) writes this file with CRLF, while every pattern below — and the
 * `allow …;\n` terminator in particular — is written against LF. Without this,
 * `allowClause()` matched nothing, every clause came back as an empty string,
 * and 32 checks failed on a machine whose rules were perfectly correct (CI runs
 * on Linux, so it never saw it). Normalize here rather than teaching each
 * pattern about `\r\n`.
 */
const source = readFileSync(new URL('firestore.rules', ROOT), 'utf8').replace(/\r\n/g, '\n')

/** Comments mention rule text (e.g. the escalation bug); only code counts. */
const stripComments = (s) =>
  s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '')

const code = stripComments(source)

/** Every `match /name/{id} { … }`, with the body brace-matched. */
function extractMatches(src) {
  const found = []
  const re = /match\s*\/(\w+)\/\{[^}]+\}\s*\{/g
  let m
  while ((m = re.exec(src)) !== null) {
    const start = m.index + m[0].length - 1 // at the opening brace
    let depth = 0
    let i = start
    for (; i < src.length; i += 1) {
      if (src[i] === '{') depth += 1
      else if (src[i] === '}') {
        depth -= 1
        if (depth === 0) break
      }
    }
    found.push({ name: m[1], start: m.index, body: src.slice(start, i + 1) })
  }
  return found
}

const matches = extractMatches(code)

function blocks(name) {
  return matches.filter((m) => m.name === name).map((m) => m.body)
}

function block(name) {
  const found = blocks(name)
  expect(found.length, `no match block for /${name}/ in firestore.rules`).toBeGreaterThan(0)
  return found.join('\n')
}

/** The `allow <op>: if …;` clause for one operation. */
function allowClause(name, op) {
  const m = block(name).match(new RegExp(`allow\\s+${op}\\s*:\\s*if([\\s\\S]*?);\\n`))
  return m ? m[1] : ''
}

/** Client source, for working out which collections the app actually uses. */
function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = new URL(entry.name + (entry.isDirectory() ? '/' : ''), dir)
    if (entry.isDirectory()) walk(path, out)
    // Test files are not client code — and this file's own examples of
    // collection(...) calls would otherwise be scanned as if they were.
    else if (/\.jsx?$/.test(entry.name) && !entry.name.endsWith('.test.js')) out.push(path)
  }
  return out
}

const clientCollections = new Set()
const clientSubcollections = new Set()
for (const file of walk(new URL('src/', ROOT))) {
  const text = readFileSync(file, 'utf8')
  for (const m of text.matchAll(/(?:collection|doc)\(\s*db\s*,\s*'([a-z_]+)'/g)) {
    clientCollections.add(m[1])
  }
  // collection(db, 'parent', someVar, 'child')
  for (const m of text.matchAll(/collection\(\s*db\s*,\s*'([a-z_]+)'\s*,\s*[^,]+,\s*'([a-z_]+)'/g)) {
    clientCollections.add(m[1])
    clientSubcollections.add(`${m[1]}/${m[2]}`)
  }
}

// Collections whose rules exist ahead of the code that will use them. They
// grant access to data no client writes, so nothing exercises them; the check
// below is what keeps that claim honest.
const INERT = [
  'generated_materials',
  'deliveries',
  'subscriptions',
  'classrooms',
  'quizzes',
  'quiz_attempts',
  'schools',
  'school_codes',
]

describe('every collection the app uses is guarded', () => {
  it('finds collections in the client source', () => {
    // Guards the scanner itself: a regex that silently matches nothing would
    // make the next test vacuously true.
    expect(clientCollections.size).toBeGreaterThanOrEqual(11)
  })

  it.each([...clientCollections].sort())('/%s/ has a rule', (name) => {
    expect(blocks(name).length, `the app writes '${name}' but firestore.rules has no match block for it`).toBeGreaterThan(0)
  })

  it('covers the subcollections the app writes', () => {
    for (const path of clientSubcollections) {
      const [parent, child] = path.split('/')
      expect(block(parent), `${path} is written by the app`).toContain(`match /${child}/`)
    }
  })
})

describe('privilege escalation cannot come back', () => {
  // The one rule that must never be relaxed: isApproved() and isAdmin() read
  // users/{uid}, so a client able to create its own profile with
  // status:'approved' (or role:'admin') bypasses the entire file.
  it('users create forces status pending and role member', () => {
    const create = allowClause('users', 'create')
    expect(create, 'users create must constrain the document, not just the uid').toContain("status == 'pending'")
    expect(create).toContain("role == 'member'")
  })

  it('users self-update cannot change role, status or schoolId', () => {
    expect(allowClause('users', 'update')).toContain("hasAny(['role', 'status', 'schoolId'])")
  })

  it('no rule grants unconditional access', () => {
    // `allow write: if true`, `allow read: if true`, or a bare `if true`.
    expect(code).not.toMatch(/if\s+true\s*[;)]/)
    expect(code).not.toMatch(/allow\s+\w+\s*:\s*if\s*;/)
  })
})

describe('like tallies cannot be tampered with', () => {
  // hasOnly(...) restricts which FIELDS may change, not what they contain: on
  // its own it lets a member set likesCount to 9999 or stuff likedBy with other
  // people's uids. likeDelta forces ±1 and only the caller's own uid.
  const LIKE_FIELDS = {
    posts: 'likesCount',
    articles: 'likesCount',
    notes: 'likes',
  }

  it.each(Object.entries(LIKE_FIELDS))('%s checks likeDelta(%s)', (name, field) => {
    const update = allowClause(name, 'update')
    expect(update, `${name} update must call likeDelta('${field}')`).toContain(`likeDelta('${field}')`)
  })

  it.each(Object.entries(LIKE_FIELDS))('%s restricts the like diff to the tally fields', (name, field) => {
    const update = allowClause(name, 'update')
    const expected = field === 'likesCount' ? "['likedBy', 'likesCount']" : `['likes', 'likesBy']`
    expect(update, `${name} update must limit the like diff to ${expected}`).toContain(expected)
  })

  it('defines likeDelta with the size and membership guards', () => {
    const fn = code.match(/function\s+likeDelta[\s\S]*?\n\s{4}\}/)
    expect(fn, 'likeDelta() is referenced but not defined').toBeTruthy()
    for (const guard of ['hasAll', 'size()']) {
      expect(fn[0], `likeDelta must use ${guard}`).toContain(guard)
    }
  })

  it('quote_likes pins the new document to the caller', () => {
    const create = allowClause('quote_likes', 'create')
    expect(create).toContain('count == 1')
    expect(create).toContain('likedBy.size() == 1')
    expect(create).toContain('request.auth.uid in request.resource.data.likedBy')
  })
})

describe('authorship is pinned on create and preserved on update', () => {
  const AUTHORED = [
    'posts',
    'articles',
    'notes',
    'weekly_forecasts',
    'lesson_plans',
    'questions',
    'lesson_slides',
    'vacancies',
  ]

  it.each(AUTHORED)('%s create authors the doc as the caller', (name) => {
    expect(allowClause(name, 'create'), `${name} create must pin authorId`).toContain(
      'request.resource.data.authorId == request.auth.uid'
    )
  })

  it.each(AUTHORED)('%s owner-update cannot reassign the author', (name) => {
    expect(allowClause(name, 'update'), `${name} update must call keepsAuthor()`).toContain('keepsAuthor()')
  })

  it('defines keepsAuthor against the changed-key diff', () => {
    // diff() only reports keys whose value actually changes, so a form writing
    // an unchanged authorId back still passes — assert that specifically,
    // because a naive `data.authorId == resource.data.authorId` would work too
    // but this is the guard that was chosen.
    const fn = code.match(/function\s+keepsAuthor[\s\S]*?\n\s{4}\}/)
    expect(fn).toBeTruthy()
    expect(fn[0]).toContain('authorId')
    expect(fn[0]).toContain('changedKeys()')
  })
})

describe('un-filtered list queries stay legal', () => {
  // Firestore is not a filter: for a list query it must be able to prove the
  // rule true for every document the query could return. A read rule that
  // depends on document data therefore denies the WHOLE query — not just the
  // documents that fail it. `isApprovedOrAdmin() && (resource.data.status ==
  // 'published' || …)` broke every un-filtered list in the app, and only for
  // non-admins, so an admin testing the portal would never see it.
  const unfiltered = new Set()
  for (const file of walk(new URL('src/', ROOT))) {
    const text = readFileSync(file, 'utf8')
    // Both list hooks: the paged one has the same duty to stay provable.
    for (const m of text.matchAll(/use(?:Paged)?Collection\(\s*'([a-z_]+)'\s*,\s*\{([^}]*)\}/g)) {
      if (!m[2].includes('filters')) unfiltered.add(m[1])
    }
    for (const m of text.matchAll(/getDocs\(\s*query\(\s*collection\(\s*db\s*,\s*'([a-z_]+)'\s*\)\s*\)/g)) {
      unfiltered.add(m[1])
    }
    for (const m of text.matchAll(/onSnapshot\(\s*collection\(\s*db\s*,\s*'([a-z_]+)'\s*\)/g)) {
      unfiltered.add(m[1])
    }
  }

  it('finds the un-filtered list queries', () => {
    expect([...unfiltered].length).toBeGreaterThanOrEqual(4)
  })

  it('scopes every list query against a collection whose read rule needs it', () => {
    // The three collections whose read rule depends on `visibility`. Listing any
    // of them without a filter is denied for every ordinary member, so the
    // scanner above must not find one — and this names them, so deleting the
    // filter fails with an explanation instead of a permission error in prod.
    const GATED = ['notes', 'lesson_plans', 'weekly_forecasts']
    for (const name of GATED) {
      expect([...unfiltered], `/${name}/ is listed un-filtered somewhere in src/`).not.toContain(name)
    }
    // …and the rule each of them relies on really is document-dependent.
    for (const name of GATED) {
      const read = allowClause(name, 'read')
      expect(read, `/${name}/ read must require the shared visibilities`).toContain(
        "resource.data.visibility in ['members', 'public']"
      )
      expect(read, `/${name}/ read must keep the author's own drafts readable`).toContain(
        'isOwner(resource.data.authorId)'
      )
      expect(read, `/${name}/ read must keep admins able to read one document`).toContain('isAdmin()')
    }
  })

  it('the paged list hook never lists a gated collection un-filtered', () => {
    const hooks = readFileSync(new URL('src/hooks/useCollection.js', ROOT), 'utf8')
    // The hook itself always orders and limits; the filter comes from the page.
    expect(hooks).toContain('startAfter')
    expect(hooks).toContain("orderBy(sort, 'desc')")
    for (const file of walk(new URL('src/pages/', ROOT))) {
      const text = readFileSync(file, 'utf8')
      for (const m of text.matchAll(/usePagedCollection\(\s*'([a-z_]+)'[\s\S]{0,400}?\}\)/g)) {
        const gated = ['notes', 'lesson_plans', 'weekly_forecasts'].includes(m[1])
        if (gated) {
          expect(m[0], `${file.pathname.split('/').pop()} lists /${m[1]}/ through the paged hook without filters`)
            .toContain('filters')
        }
      }
    }
  })

  it('Search asks for the scoped slice of each collection the rules gate', () => {
    const search = readFileSync(new URL('src/pages/Search.jsx', ROOT), 'utf8')
    for (const name of ['lesson_plans', 'notes', 'weekly_forecasts']) {
      expect(search, `Search.jsx no longer marks ${name} as scoped`).toContain(`name: '${name}', scoped: true`)
    }
    expect(search).toContain("where('authorId', '==', uid)")
    expect(search).toContain("['visibility', 'in', ['members', 'public']]")
  })

  it('the visibility a form can choose is the vocabulary the rules allow', () => {
    const forms = ['src/pages/NoteForm.jsx', 'src/pages/LessonPlanForm.jsx', 'src/pages/ForecastForm.jsx']
    for (const file of forms) {
      const text = readFileSync(new URL(file, ROOT), 'utf8')
      const options = [...text.matchAll(/<option value="(\w+)"/g)].map((m) => m[1])
      expect(options, `${file} lost its privacy choice`).toContain('private')
      expect(options).toContain('members')
      // Every value a form can write must be one the read rule recognises.
      const allowed = ['members', 'public', 'private']
      expect(options.filter((o) => !allowed.includes(o)), `${file} writes an unknown visibility`).toEqual([])
    }
  })

  it.each([...unfiltered].sort())('/%s/ read does not require document data', (name) => {
    const read = allowClause(name, 'read')
    // A query is provable when one of its disjuncts holds whatever the document
    // contains, for an ordinary approved member. `isAdmin()` does NOT count:
    // it is document-independent but false for a member, so the member's list
    // query still fails.
    const MEMBER_PATH = /is(?:ApprovedOrAdmin|Approved|SignedIn)\(\)/
    const NAKED = /^\s*is(?:ApprovedOrAdmin|Approved|SignedIn)\(\)\s*$/
    const DISJUNCT = /\|\|\s*is(?:ApprovedOrAdmin|Approved|SignedIn)\(\)/

    expect(
      NAKED.test(read) || DISJUNCT.test(read),
      `the read rule for ${name} has no document-independent branch, so the un-filtered list query in the client is denied for every non-admin member. Clause: ${read.trim()}`
    ).toBe(true)
  })
})

describe('the file is structurally sound', () => {
  it('declares rules_version 2 and a single service block', () => {
    expect(source.trimStart().startsWith("rules_version = '2';")).toBe(true)
    expect(code.match(/service cloud\.firestore/g)).toHaveLength(1)
  })

  it('balances every bracket', () => {
    for (const [open, close] of [['{', '}'], ['(', ')'], ['[', ']']]) {
      const a = code.split(open).length - 1
      const b = code.split(close).length - 1
      expect(a, `${open}${close} unbalanced`).toBe(b)
    }
  })

  it('calls no helper that is not defined', () => {
    const defined = new Set([...code.matchAll(/function\s+(\w+)\s*\(/g)].map((m) => m[1]))
    const LANGUAGE = new Set([
      'if', 'return', 'get', 'exists', 'hasOnly', 'hasAll', 'hasAny', 'size', 'keys', 'diff',
      'affectedKeys', 'match', 'allow', 'function', 'in', 'request', 'resource',
    ])
    const called = new Set([...code.matchAll(/(?<![\w.])(\w+)\s*\(/g)].map((m) => m[1]))
    const undefinedCalls = [...called].filter((c) => !defined.has(c) && !LANGUAGE.has(c))
    expect(undefinedCalls, 'these look like helper calls with no definition').toEqual([])
  })

  it('every allow statement is terminated', () => {
    expect(code).not.toMatch(/allow\s+\w+(?:\s*,\s*\w+)*\s*:[^;]*?\n\s*(?:allow|match|\})/)
  })
})

describe('rules kept ahead of their phase stay inert', () => {
  it.each(INERT)('%s is not referenced by the client yet', (name) => {
    // If this fails, that phase has started: re-read its rule block against the
    // new client code before trusting it (see docs/security.md).
    expect(
      clientCollections.has(name),
      `src/ now writes '${name}' — review its rule block against the real code before relying on the INERT comment`
    ).toBe(false)
  })
})
