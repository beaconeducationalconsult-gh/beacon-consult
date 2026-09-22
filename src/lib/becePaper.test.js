import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { BECE_FORMAT, composeBecePaper, composePaper1, composePaper2 } from './becePaper'

/*
 * The BECE mock, held to the bank it actually prints from.
 *
 * The served JHS files are the pool a B9 teacher really gets, so the tests
 * read them straight from `public/curriculum/` the way the bundle contract
 * tests do: if the bank's shape drifts, these fail before a teacher does.
 * The synthetic packs at the bottom hold the honesty rules (shortfalls are
 * named, never padded) against pools small enough to force them.
 */

const pack = (grade) =>
  JSON.parse(
    readFileSync(new URL(`../../public/curriculum/questions/mathematics/${grade}.json`, import.meta.url), 'utf8'),
  )

const PACKS = [
  { grade: 'B7', items: pack('B7').items },
  { grade: 'B8', items: pack('B8').items },
  { grade: 'B9', items: pack('B9').items },
]

const JHS = () => composeBecePaper(PACKS)

describe('the BECE format', () => {
  it('is the one WAEC sets for the Common Core', () => {
    expect(BECE_FORMAT.paper1).toEqual({ count: 40, marksEach: 1, minutes: 60 })
    expect(BECE_FORMAT.paper2).toEqual({ count: 6, answerCount: 4, marksEach: 15, minutes: 60 })
    expect(BECE_FORMAT.totalMarks).toBe(100)
  })
})

describe('Paper 1, from the real JHS bank', () => {
  it('prints exactly 40 single-mark objectives, none repeated', () => {
    const { questions, marks, shortfall } = composePaper1(PACKS)
    expect(questions).toHaveLength(40)
    expect(questions.every((q) => q.type === 'mcq')).toBe(true)
    expect(new Set(questions.map((q) => q.id)).size).toBe(40)
    expect(questions.every((q) => (q.options || []).length >= 2)).toBe(true)
    expect(marks).toBe(40)
    expect(shortfall).toBeNull()
  })

  it('draws on all three years, balanced', () => {
    const { gradeSpread } = composePaper1(PACKS)
    expect(Object.keys(gradeSpread).sort()).toEqual(['B7', 'B8', 'B9'])
    for (const count of Object.values(gradeSpread)) {
      expect(count).toBeGreaterThanOrEqual(10)
      expect(count).toBeLessThanOrEqual(20)
    }
  })

  it('is deterministic — same banks, same paper', () => {
    expect(composePaper1(PACKS).questions).toEqual(composePaper1(PACKS).questions)
  })

  it('spreads one question per indicator before any indicator twice', () => {
    const { questions } = composePaper1(PACKS)
    const codes = questions.map((q) => q.indicatorCode)
    expect(new Set(codes).size).toBeGreaterThanOrEqual(38) // the sweep, not a topic drill
  })
})

describe('Paper 2, from the real JHS bank', () => {
  it('prints six questions of exactly 15 marks each', () => {
    const { questions, marks, printed, shortfall } = composePaper2(PACKS)
    expect(questions).toHaveLength(6)
    for (const question of questions) {
      expect(question.marks).toBe(15)
      expect(question.parts.reduce((sum, part) => sum + part.marks, 0)).toBe(15)
      expect(question.parts.length).toBeGreaterThanOrEqual(2)
      expect(question.parts.length).toBeLessThanOrEqual(5)
    }
    // The sheet prints 90 marks' worth of questions; the sitting counts the
    // four a candidate answers — 60, which is what carries to the total.
    expect(printed).toBe(90)
    expect(marks).toBe(60)
    expect(shortfall).toBeNull()
  })

  it('letters the parts (a), (b)… easiest first', () => {
    const { questions } = composePaper2(PACKS)
    for (const question of questions) {
      question.parts.forEach((part, index) => {
        expect(part.letter).toBe(String.fromCharCode(97 + index))
      })
      const marks = question.parts.map((part) => part.marks)
      expect(marks).toEqual([...marks].sort((a, b) => a - b))
    }
  })

  it('uses no question twice, across both papers', () => {
    const paper = JHS()
    const ids = [
      ...paper.paper1.questions.map((q) => q.id),
      ...paper.paper2.questions.flatMap((q) => q.parts.map((p) => p.question.id)),
    ]
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('keeps a question inside one grade, so it reads as one syllabus level', () => {
    const { questions } = composePaper2(PACKS)
    for (const question of questions) {
      const grades = new Set(question.parts.map((p) => p.question.id?.split('.')[0]))
      expect(grades.size).toBe(1)
    }
  })

  it('carries an essay in at least one question — Section-style depth, not all one-liners', () => {
    const { questions } = composePaper2(PACKS)
    expect(questions.some((q) => q.parts.some((p) => p.question.type === 'essay'))).toBe(true)
  })

  it('is deterministic', () => {
    expect(composePaper2(PACKS).questions).toEqual(composePaper2(PACKS).questions)
  })
})

describe('the whole sitting', () => {
  const paper = JHS()

  it('adds to the 100 marks the exam promises', () => {
    expect(paper.totalMarks).toBe(100)
  })

  it('asks about the JHS syllabus broadly, not one strand', () => {
    // 159 indicators across B7–B9 mathematics; a mock that touches a third of
    // them is a revision paper, not a re-drill of week one.
    expect(paper.indicators).toBeGreaterThanOrEqual(50)
  })
})

describe('honesty when the pool runs short', () => {
  it('names a Paper 1 shortfall instead of padding with non-objectives', () => {
    const thin = [{ grade: 'B7', items: PACKS[0].items.filter((q) => q.type === 'mcq').slice(0, 10) }]
    const result = composePaper1(thin)
    expect(result.questions).toHaveLength(10)
    expect(result.shortfall).toContain('30')
    expect(result.shortfall).toContain('objective')
  })

  it('prints the structured questions it can and says what is missing', () => {
    const thin = PACKS.map(({ grade, items }) => ({
      grade,
      items: items.filter((q) => q.type !== 'mcq').slice(0, 6),
    }))
    const result = composePaper2(thin)
    expect(result.questions.length).toBeLessThan(6)
    expect(result.shortfall).toContain('structured questions')
  })

  it('never prints a question below the 15 marks the format promises', () => {
    const thin = PACKS.map(({ grade, items }) => ({
      grade,
      items: items.filter((q) => q.type !== 'mcq').slice(0, 6),
    }))
    for (const question of composePaper2(thin).questions) {
      expect(question.marks).toBe(15)
    }
  })
})
