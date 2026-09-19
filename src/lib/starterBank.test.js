import { describe, expect, it } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { starterToFirestore } from './starterBank'

/*
 * The starter bank is generated (scripts/generate_question_bank.py) and served
 * (scripts/build_question_bank.py); the app's half is the document it becomes.
 * These hold that half, plus the bundle contract the app reads: the index and
 * the files have to agree, and every question has to hang off a served
 * indicator — otherwise the import would create orphans in Firestore.
 */

const root = new URL('../../public/curriculum/', import.meta.url)
const read = (path) => JSON.parse(readFileSync(new URL(path, root), 'utf8'))

describe('the served starter bank', () => {
  const index = read('questions/_index.json')

  it('lists files that exist and counts that match', () => {
    let total = 0
    for (const [subject, grades] of Object.entries(index.subjects)) {
      for (const [grade, counts] of Object.entries(grades)) {
        const path = `questions/${subject}/${grade}.json`
        expect(existsSync(new URL(path, root)), `${path} is in the index but missing`).toBe(true)
        const pack = read(path)
        expect(pack.items.length, `${path} count`).toBe(counts.questions)
        expect(new Set(pack.items.map((i) => i.indicatorCode)).size, `${path} coverage`).toBe(counts.coveredIndicators)
        total += pack.items.length
      }
    }
    expect(total).toBe(index.totals.questions)
  })

  it('hangs every question off a served indicator of its own subject', () => {
    for (const [subject, grades] of Object.entries(index.subjects)) {
      for (const grade of Object.keys(grades)) {
        const codes = new Set(
          read(`${grade.toLowerCase()}_indicators.json`)
            .filter((row) => row.subjectId === subject)
            .map((row) => row.code)
        )
        for (const item of read(`questions/${subject}/${grade}.json`).items) {
          expect(codes.has(item.indicatorCode), `${subject} ${grade}: ${item.indicatorCode}`).toBe(true)
        }
      }
    }
  })

  it('serves a JHS bank, not just a primary one', () => {
    // B7-B9 used to be empty on purpose: the primary rules are arithmetic, and at
    // JHS the same words sit inside algebra and geometry indicators. The JHS rules
    // exist now, and this holds them in place — a grade that quietly lost its bank
    // (or a rule that stopped firing) fails here rather than in a teacher's paper.
    for (const grade of ['B7', 'B8', 'B9']) {
      const pack = read(`questions/mathematics/${grade}.json`)
      expect(pack.items.length, `${grade} items`).toBeGreaterThanOrEqual(60)
      expect(pack.coveredIndicators, `${grade} coverage`).toBeGreaterThanOrEqual(25)
      expect(read('questions/_index.json').subjects.mathematics[grade].questions).toBe(pack.items.length)
    }
  })

  it('labels every generated item with the rule that produced it', () => {
    // The provenance is the review surface: a teacher (or an audit) reads the
    // rule, not 376 items. Authored items carry `authored` instead.
    for (const [subject, grades] of Object.entries(index.subjects)) {
      for (const grade of Object.keys(grades)) {
        for (const item of read(`questions/${subject}/${grade}.json`).items) {
          expect(['authored', 'generated'], `${item.id} source kind`).toContain(
            String(item.source).split(':')[0]
          )
          if (String(item.source).startsWith('generated:')) {
            expect(String(item.source), `${item.id} rule id`).toMatch(/^generated:[a-z0-9-]+$/)
          }
          expect(item.indicatorCode.startsWith(grade), `${item.id} hangs off another grade`).toBe(true)
        }
      }
    }
  })

  it('gives every multiple-choice question an answer among its options', () => {
    for (const [subject, grades] of Object.entries(index.subjects)) {
      for (const grade of Object.keys(grades)) {
        for (const item of read(`questions/${subject}/${grade}.json`).items) {
          if (item.type !== 'mcq') continue
          expect(item.options.length, item.id).toBeGreaterThanOrEqual(2)
          expect(item.options, `${item.id} answer`).toContain(item.answer)
        }
      }
    }
  })
})

describe('a starter question becomes a firestore document', () => {
  const item = {
    id: 'B4.1.1.1.1-generated-1',
    indicatorCode: 'B4.1.1.1.1',
    prompt: 'What is the value of the digit 9 in 93,229?',
    type: 'mcq',
    options: ['9,000', '90,000', '900', '9'],
    answer: '90,000',
    marks: 1,
    difficulty: 'core',
    source: 'generated:place-value',
  }

  it('carries the fields the bank, the quiz and the paper read', () => {
    const doc = starterToFirestore(item, {
      subjectId: 'mathematics', subjectName: 'Mathematics', grade: 'B4',
      authorId: 'uid1', authorName: 'Mr Mensah',
    })
    expect(doc).toMatchObject({
      subjectId: 'mathematics',
      subjectName: 'Mathematics',
      grade: 'B4',
      type: 'mcq',
      prompt: item.prompt,
      answer: '90,000',
      marks: 1,
      term: 1,
      status: 'published',
      authorId: 'uid1',
    })
    // The curriculum link is the code list QuestionBank and questionPaper read.
    expect(doc.indicatorCodes).toEqual(['B4.1.1.1.1'])
    // indicatorIds holds whole records in the form, so an import leaves it empty.
    expect(doc.indicatorIds).toEqual([])
  })

  it('keeps the provenance, so generated is never mistaken for authored', () => {
    const doc = starterToFirestore(item, { subjectId: 'mathematics', grade: 'B4', authorId: 'uid1' })
    expect(doc.source).toBe('generated:place-value')
    expect(doc.starterBankId).toBe(item.id)
    // …and a hand-written item is labelled as such.
    const authored = starterToFirestore({ ...item, source: 'authored' }, { subjectId: 'mathematics', grade: 'B4', authorId: 'uid1' })
    expect(authored.source).toBe('authored')
  })

  it('defaults what a hand-written item may omit', () => {
    const doc = starterToFirestore(
      { id: 'x', indicatorCode: 'B4.1.1.1.1', prompt: 'p', type: 'short', answer: 'a' },
      { subjectId: 'mathematics', grade: 'B4', authorId: 'uid1' }
    )
    expect(doc.marks).toBe(1)
    expect(doc.difficulty).toBe('core')
    expect(doc.options).toEqual([])
    expect(doc.answer).toBe('a')
    expect(doc.authorName).toBe('Member')
    expect(doc.subjectName).toBe('mathematics')
  })
})
