import { readFileSync, readdirSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

/*
 * Every list query in the app has the composite index it needs.
 *
 * This is the one class of bug that is invisible until production. A page that
 * adds `where('status','==',…)` to an already-ordered list works in dev, works
 * in the emulator (which does not demand composite indexes), and in production
 * fails for everyone with `failed-precondition` — a list that shows nothing,
 * with the reason only in the browser console. The console error carries a
 * one-click index link; until someone clicks it, the page is broken.
 *
 * So the requirement is computed from the source rather than listed by hand:
 *
 *   1. every `useCollection` / `usePagedCollection` call site — the app's lists.
 *      `ordered: true` (or the paged hook, which always orders) means the server
 *      sorts, and a server-sorted query with a filter needs a composite index;
 *   2. every hand-written `query(collection(db, '…'), where(…), orderBy(…))`;
 *   3. `firebase.json` and `.firebaserc` still point at the files they deploy.
 *
 * Equality fields may be in any order in the index — Firestore matches them as
 * a set — but the `orderBy` field must be last and descending, which is how
 * `firestore.indexes.json` writes all of them.
 *
 * Two equality filters and no `orderBy` are required to have an index as well.
 * Strictly, Firestore can sometimes merge single-field indexes for equality-only
 * queries; the console has asked for a composite one here anyway (`questions |
 * authorId, weekKey` in this file came from exactly that), and an index that is
 * not needed costs a little write amplification while a missing one costs a
 * broken page.
 */

const ROOT = new URL('..', import.meta.url)
const read = (path) => readFileSync(new URL(path, ROOT), 'utf8').replace(/\r\n/g, '\n')

const indexes = JSON.parse(read('firestore.indexes.json')).indexes
const firebaseJson = JSON.parse(read('firebase.json'))
const firebaserc = JSON.parse(read('.firebaserc'))

/** The text inside the brackets/parens that open at `open`, string-aware. */
function balanced(source, open) {
  const closer = { '(': ')', '[': ']', '{': '}' }[source[open]]
  let depth = 0
  let quote = null
  for (let i = open; i < source.length; i += 1) {
    const ch = source[i]
    if (quote) {
      if (ch === '\\') i += 1
      else if (ch === quote) quote = null
      continue
    }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue }
    if (ch === '(' || ch === '[' || ch === '{') depth += 1
    else if (ch === ')' || ch === ']' || ch === '}') {
      depth -= 1
      if (depth === 0) return { body: source.slice(open + 1, i), end: i, closer }
    }
  }
  throw new Error(`unbalanced ${source[open]} at ${open}`)
}

/** Split on top-level commas — `a, { b: [1, 2] }` is two arguments. */
function topLevelSplit(text) {
  const parts = []
  let start = 0
  let depth = 0
  let quote = null
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i]
    if (quote) {
      if (ch === '\\') i += 1
      else if (ch === quote) quote = null
      continue
    }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue }
    if (ch === '(' || ch === '[' || ch === '{') depth += 1
    else if (ch === ')' || ch === ']' || ch === '}') depth -= 1
    else if (ch === ',' && depth === 0) { parts.push(text.slice(start, i)); start = i + 1 }
  }
  parts.push(text.slice(start))
  return parts.map((part) => part.trim()).filter(Boolean)
}

/**
 * Split on top-level `?` and `:`, so a ternary's branches are read as
 * alternatives. `scope === 'mine' ? [['authorId','==',uid]] : SHARED` is one
 * query with one filter, not a query filtered on both.
 */
function alternatives(text) {
  const parts = []
  let start = 0
  let depth = 0
  let quote = null
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i]
    if (quote) {
      if (ch === '\\') i += 1
      else if (ch === quote) quote = null
      continue
    }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue }
    if (ch === '(' || ch === '[' || ch === '{') depth += 1
    else if (ch === ')' || ch === ']' || ch === '}') depth -= 1
    else if ((ch === '?' || ch === ':') && depth === 0) { parts.push(text.slice(start, i)); start = i + 1 }
  }
  parts.push(text.slice(start))
  return parts.map((part) => part.trim()).filter(Boolean)
}

/** The value of `key:` in an options object, as source text. */
function optionValue(options, key) {
  const re = new RegExp(`(?:^|[{,\\s])${key}\\s*:`)
  const match = re.exec(options)
  if (!match) return null
  const from = match.index + match[0].length
  return topLevelSplit(options.slice(from))[0]
}

const filterLiteral = /\[\s*'([A-Za-z_][\w]*)'\s*,\s*'(==|in|array-contains(?:-any)?|!=|<|<=|>|>=)'/g

/**
 * The `[field, op, value]` filters an expression asks for, following one level
 * of local constants — `filters: scope === 'mine' ? [['authorId','==',uid]] : SHARED`
 * yields both branches, because the test needs the query to be provable either way.
 */
function filtersIn(expression, source) {
  const found = []
  const seen = new Set()
  const scan = (text) => {
    for (const match of text.matchAll(filterLiteral)) found.push({ field: match[1], op: match[2] })
    // Constants in the same file (`const SHARED = [...]`), one level deep.
    for (const name of new Set([...text.matchAll(/\b([A-Z][A-Z0-9_]{2,})\b/g)].map((m) => m[1]))) {
      if (seen.has(name)) continue
      seen.add(name)
      const declaration = new RegExp(`const\\s+${name}\\s*=\\s*`)
      const at = declaration.exec(source)
      if (!at) continue
      const start = at.index + at[0].length
      if (source[start] === '[' || source[start] === '(') scan(balanced(source, start).body)
    }
  }
  scan(expression)
  return found
}

/** `{ collection, filters, sortedBy }` from one call site, or null if dynamic. */
function requirementFrom({ file, source, hook, options }) {
  const nameMatch = /^\s*'([^']+)'/.exec(options.collection)
  let collections = nameMatch ? [nameMatch[1]] : []
  if (!collections.length) {
    // A variable: the sections list in the same file, e.g. `<ContributionsSection {...section} />`
    // over `SECTIONS = [{ collection: 'notes', … }]`. Every one of them is a query.
    collections = [...source.matchAll(/collection:\s*'([^']+)'/g)].map((m) => m[1])
  }
  if (!collections.length) return null

  const filterText = optionValue(options.rest, 'filters') || ''
  const sortText = optionValue(options.rest, 'sort')
  const sort = sortText ? sortText.replace(/['"]/g, '') : 'createdAt'
  const ordered = hook === 'usePagedCollection' || /ordered:\s*true/.test(options.rest)

  // One requirement per branch: the Mine tab and the Shared tab are two queries
  // with two different index needs, and both have to be answerable.
  const variants = alternatives(filterText)
  const branches = variants.length ? variants.slice(variants.length === 1 ? 0 : 1) : ['']
  return branches.flatMap((branch) => collections.map((collection) => ({
    file, collection, filters: filtersIn(branch, source), sort, ordered: ordered && Boolean(sort),
  })))
}

/** Every list query in `src/`, as `{ file, collection, filters, sort, ordered }`. */
function listQueries() {
  const files = [
    ...readdirSync(new URL('src/pages', ROOT)).filter((f) => f.endsWith('.jsx')).map((f) => `src/pages/${f}`),
  ]
  const rows = []
  for (const file of files) {
    const source = read(file)

    // 1. The list hooks.
    const hookRe = /use(PagedCollection|Collection)\(/g
    for (const match of source.matchAll(hookRe)) {
      const hook = `use${match[1]}`
      const open = match.index + match[0].length - 1
      const args = topLevelSplit(balanced(source, open).body)
      const options = { collection: args[0] ?? '', rest: args.slice(1).join(', ') }
      for (const req of requirementFrom({ file, source, hook, options }) || []) rows.push(req)
    }

    // 2. Hand-written queries that name their collection literally. The generic
    //    ones in src/hooks/useCollection.js build theirs from a parameter, and
    //    Search.jsx feeds its filters in from a helper, so both are skipped —
    //    they are equality-only, which needs no composite index. `searchSites`
    //    below keeps that honest.
    for (const match of source.matchAll(/\bquery\(/g)) {
      const open = match.index + match[0].length - 1
      const body = balanced(source, open).body
      const name = /collection\(\s*(?:db\s*,\s*)?'([^']+)'/.exec(body)
      if (!name) continue
      const clauses = body.slice(body.indexOf(name[0]) + name[0].length)
      const filters = [...clauses.matchAll(/where\(\s*'([\w]+)'\s*,\s*'([^']+)'/g)].map((m) => ({ field: m[1], op: m[2] }))
      const sortMatch = /orderBy\(\s*'([\w]+)'\s*,\s*'(asc|desc)'/.exec(clauses)
      const ordered = Boolean(sortMatch) && sortMatch[2] === 'desc'
      rows.push({ file, collection: name[1], filters, sort: sortMatch ? sortMatch[1] : 'createdAt', ordered })
    }
  }
  return rows
}

const queries = listQueries()

/** Does `index` serve the query? Equality group first (any order), sort field last. */
function serves(index, query) {
  if (index.collectionGroup !== query.collection) return false
  const fields = index.fields || []
  const equalities = query.filters.map((f) => ({
    field: f.field,
    kind: f.op === 'array-contains' || f.op === 'array-contains-any' ? 'CONTAINS' : 'ASCENDING',
  }))
  const satisfied = (candidate) => equalities.every((eq) => candidate.some(
    (field) => field.fieldPath === eq.field && (eq.kind === 'CONTAINS' ? field.arrayConfig === 'CONTAINS' : field.order === 'ASCENDING')
  ))

  if (!query.ordered || !equalities.length) {
    // Equality-only (and no `orderBy`): an index over those fields, longer ones included.
    return equalities.length > 1 && satisfied(fields)
  }
  const last = fields[fields.length - 1]
  if (!last || last.fieldPath !== query.sort || last.order !== 'DESCENDING') return false
  return satisfied(fields.slice(0, -1))
}

describe('every list query has its composite index', () => {
  it('reads the queries and the index file, rather than assuming them', () => {
    expect(indexes.length).toBeGreaterThan(10)
    expect(queries.length).toBeGreaterThanOrEqual(18)
    const collections = new Set(queries.map((q) => q.collection))
    // The collections P0-2 is about: the three visibility-gated ones, the paged
    // ones, and the library. If a scan stops finding them, this fails first.
    expect([...collections]).toEqual(expect.arrayContaining([
      'notes', 'lesson_plans', 'weekly_forecasts', 'questions', 'generated_documents', 'articles', 'posts',
    ]))
  })

  it('requires the index for exactly the queries that need one', () => {
    const needs = queries.filter((q) => (q.ordered && q.filters.length) || q.filters.length > 1)
    expect(needs.length).toBeGreaterThanOrEqual(10)
    const missing = needs
      .filter((q) => !indexes.some((index) => serves(index, q)))
      .map((q) => `${q.file}: ${q.collection} where(${q.filters.map((f) => `${f.field} ${f.op}`).join(', ')})`
        + `${q.ordered ? ` orderBy(${q.sort} desc)` : ''}`)
    expect(missing, `no composite index in firestore.indexes.json for:\n  ${missing.join('\n  ')}`).toEqual([])
  })

  it('does not demand an index for an unfiltered or single-filter list', () => {
    // The other direction: `notes` ordered with no filter is served by the
    // automatic single-field index, and requiring one here would mean writing
    // the test wrong rather than the index.
    for (const query of queries.filter((q) => !q.filters.length)) {
      expect(indexes.some((index) => serves(index, query))).toBe(false)
    }
  })
})

describe('the deployable files still line up', () => {
  it('keeps firebase.json pointing at files that exist', () => {
    expect(firebaseJson.firestore.rules).toBe('firestore.rules')
    expect(firebaseJson.firestore.indexes).toBe('firestore.indexes.json')
    expect(firebaseJson.storage.rules).toBe('storage.rules')
    for (const path of ['firestore.rules', 'firestore.indexes.json', 'storage.rules']) {
      expect(read(path).length, `${path} is missing or empty`).toBeGreaterThan(100)
    }
  })

  it('pins the project so `firebase deploy` needs no flag', () => {
    // Which project that is lives in .firebaserc alone; what matters here is that
    // it is pinned (so `make deploy-rules` cannot drift to "whatever project the
    // CLI was last used with") and that the pre-flight's comparison with
    // .env.local has something to compare. `src/deployCheck.test.js` covers the
    // comparison itself.
    expect(typeof firebaserc.projects.default).toBe('string')
    expect(firebaserc.projects.default).toMatch(/^[a-z0-9-]+$/)
  })

  it('describes every index fully — a collection, fields, and an order or array config', () => {
    for (const index of indexes) {
      expect(index.collectionGroup, 'an index with no collectionGroup').toBeTruthy()
      // Single-field entries are legal and one is in use (`posts | timestamp`).
      expect(index.fields.length, `${index.collectionGroup} has an index with no fields`).toBeGreaterThanOrEqual(1)
      for (const field of index.fields) {
        expect(field.fieldPath, `${index.collectionGroup} has a field with no path`).toBeTruthy()
        expect(Boolean(field.order) !== Boolean(field.arrayConfig), `${index.collectionGroup}.${field.fieldPath} needs exactly one of order/arrayConfig`).toBe(true)
      }
    }
    const keys = indexes.map((i) => `${i.collectionGroup}|${i.fields.map((f) => `${f.fieldPath}:${f.order || f.arrayConfig}`).join(',')}`)
    expect(new Set(keys).size, 'duplicate index entries').toBe(keys.length)
  })
})
