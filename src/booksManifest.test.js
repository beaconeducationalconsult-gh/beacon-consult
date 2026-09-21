import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

/*
 * The book rollout (P3-1) writes real .docx files into `books/`, which is
 * gitignored — the repository's record of them is `data/books_manifest.json`.
 * That makes the manifest a claim about the product, so it is held to the same
 * standard as the rest of the data: every book it names must belong to a
 * subject-grade the portal actually serves, and the generator's contract (one
 * lesson per indicator) has to hold in the numbers it reports.
 */

const root = new URL('../', import.meta.url)
const read = (path) => JSON.parse(readFileSync(new URL(path, root), 'utf8'))

const manifest = read('data/books_manifest.json')

describe('the books manifest', () => {
  it('covers every served subject-grade exactly once', () => {
    const seen = new Set()
    for (const book of manifest.books) {
      const key = `${book.subject}|${book.grade}`
      expect(seen.has(key), `${key} appears twice`).toBe(false)
      seen.add(key)
    }
    // The rollout's whole point is that books keep step with the curriculum the
    // app serves — a subject-grade in one and not the other is drift.
    const served = new Map()
    for (const grade of read('public/curriculum/grades.json')) {
      const gid = grade.id
      served.set(gid, read(`public/curriculum/${gid.toLowerCase()}_subjects.json`).map((s) => s.id))
    }
    const expected = new Set()
    for (const [grade, subjects] of served) for (const subject of subjects) expected.add(`${subject}|${grade}`)
    expect([...seen].sort()).toEqual([...expected].sort())
    expect(manifest.pairs).toBe(expected.size)
  })

  it('gives every book a textbook and a workbook, with a content hash', () => {
    for (const book of manifest.books) {
      for (const kind of ['textbook', 'workbook']) {
        const documents = book.documents[kind]
        expect(documents.length, `${book.subject} ${book.grade} ${kind}`).toBeGreaterThan(0)
        for (const document of documents) {
          expect(document.file).toMatch(new RegExp(`^${book.subject}-${kind}-skeleton(-v\\d+)?\\.docx$`))
          expect(document.bytes).toBeGreaterThan(1000)
          expect(document.contentHash).toMatch(/^[0-9a-f]{16}$/)
          expect(document.revision).toBeGreaterThanOrEqual(1)
        }
      }
    }
    expect(manifest.documents)
      .toBe(manifest.books.reduce((n, b) => n + b.documents.textbook.length + b.documents.workbook.length, 0))
  })

  it('holds the generator’s contract: one lesson per indicator', () => {
    for (const book of manifest.books) {
      const { chapters, units, lessons } = book.structure
      expect(lessons, `${book.subject} ${book.grade}`).toBe(book.indicators)
      expect(chapters).toBeGreaterThan(0)
      expect(units).toBeGreaterThan(0)
      expect(units).toBeLessThanOrEqual(lessons)
    }
  })

  it('flags any subject whose books have a second revision', () => {
    // `-v2` files are alternate revisions, not extra products: the manifest
    // lists them so a published set is never confused with a draft.
    const revised = manifest.books.filter((b) => b.revisions > 1).map((b) => `${b.subject} ${b.grade}`)
    expect(manifest.withRevisions).toEqual(revised)
  })

  it('names the pilot the ticket starts from', () => {
    expect(manifest.pilot).toEqual({ subject: 'mathematics', grade: 'B1' })
    expect(manifest.books.some((b) => b.subject === 'mathematics' && b.grade === 'B1')).toBe(true)
  })
})
