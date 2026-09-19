import { describe, expect, it } from 'vitest'
import {
  SECTION_PLAN,
  buildPool,
  composePaper,
  coverageOf,
  groupMissing,
  filterByIndicators,
  indicatorOf,
  sectionForType,
  summarise,
  termScope,
} from './examPaper'

/*
 * The composition rules, without a browser. `questionPaper.js` prints; this
 * decides. The two things a teacher would notice first if they broke are held
 * here: the paper never runs past the marks asked for, and a section is never
 * filled with the same indicator over and over while other indicators are on
 * the shelf.
 */

const q = (id, type, marks, indicator) => ({
  id,
  type,
  marks,
  indicatorCode: indicator,
  prompt: `${id}?`,
})

/** A pool with room for every section: 8 objectives, 6 short, 3 essays. */
const POOL = [
  ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => q(`m${n}`, 'mcq', 1, `B4.1.1.1.${n}`)),
  ...[1, 2, 3, 4, 5, 6].map((n) => q(`s${n}`, 'short', 3, `B4.1.2.1.${n}`)),
  ...[1, 2, 3].map((n) => q(`e${n}`, 'essay', 8, `B4.2.1.1.${n}`)),
]

describe('composePaper', () => {
  it('never prints more marks than the paper asked for', () => {
    for (const target of [20, 40, 50, 60, 80, 120]) {
      const paper = composePaper(POOL, { targetMarks: target })
      expect(paper.totalMarks, `target ${target}`).toBeLessThanOrEqual(target)
      expect(paper.targetMarks).toBe(target)
    }
  })

  it('puts each question in the section that claims its type', () => {
    const paper = composePaper(POOL, { targetMarks: 50 })
    const bySection = Object.fromEntries(paper.sections.map((s) => [s.id, s]))
    expect(bySection.A.questions.every((x) => x.type === 'mcq')).toBe(true)
    expect(bySection.B.questions.every((x) => ['short', 'truefalse'].includes(x.type))).toBe(true)
    expect(bySection.C.questions.every((x) => x.type === 'essay')).toBe(true)
  })

  it('covers indicators before it repeats one', () => {
    // Twelve objectives over four indicators: the first four taken must be one
    // per indicator, not three from the same sub-strand.
    const pool = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((n) =>
      q(`m${n}`, 'mcq', 1, `B4.1.1.1.${1 + (n % 4)}`)
    )
    const paper = composePaper(pool, { targetMarks: 50 })
    const sectionA = paper.sections[0].questions
    if (sectionA.length >= 4) {
      const firstFour = sectionA.slice(0, 4).map((x) => x.indicatorCode)
      expect(new Set(firstFour).size).toBe(4)
    }
    expect(paper.indicators).toBe(new Set(paper.questions.map((x) => x.indicatorCode)).size)
  })

  it('is deterministic — same pool, same paper', () => {
    const a = composePaper(POOL, { targetMarks: 45 })
    const b = composePaper([...POOL].reverse(), { targetMarks: 45 })
    expect(a.questions.map((x) => x.id)).toEqual(b.questions.map((x) => x.id))
  })

  it('leaves a section empty when the pool has nothing of that type', () => {
    const paper = composePaper(POOL.filter((x) => x.type === 'mcq'), { targetMarks: 50 })
    const [a, b, c] = paper.sections
    expect(a.questions.length).toBeGreaterThan(0)
    expect(b.questions).toEqual([])
    expect(c.questions).toEqual([])
    expect(paper.totalMarks).toBe(a.marks)
  })

  it('keeps a section alive when its share of the marks is smaller than one question', () => {
    // One essay of 8 marks and a 20-mark target: Section C's own share is 5, so
    // the strict pass finds nothing — but the paper has room, so it goes in.
    const paper = composePaper([q('e1', 'essay', 8, 'B4.2.1.1.1')], { targetMarks: 20 })
    const sectionC = paper.sections[2]
    expect(sectionC.questions.map((x) => x.id)).toEqual(['e1'])
    expect(paper.totalMarks).toBe(8)
    expect(paper.omitted).toEqual([])
  })

  it('leaves a section out rather than printing a bigger paper than asked for', () => {
    // The whole pool at a 20-mark target: 8 objectives and 2 shorts use 14
    // marks, and the cheapest essay (8) no longer fits — so Section C is
    // omitted, and named, instead of the paper quietly becoming a 22-mark one.
    const paper = composePaper(POOL, { targetMarks: 20 })
    const [a, b, c] = paper.sections
    expect(a.marks).toBe(8)
    expect(b.marks).toBe(6)
    expect(c.questions).toEqual([])
    expect(paper.totalMarks).toBe(14)
    expect(paper.omitted.map((x) => x.id)).toEqual(['C'])
    expect(paper.omitted[0].reason).toMatch(/8 marks/)
  })

  it('reports no omissions when the paper fits', () => {
    expect(composePaper(POOL, { targetMarks: 60 }).omitted).toEqual([])
  })

  it('handles an empty pool without throwing', () => {
    const paper = composePaper([], { targetMarks: 50 })
    expect(paper.questions).toEqual([])
    expect(paper.totalMarks).toBe(0)
    expect(paper.indicators).toBe(0)
  })

  it('treats one-mark questions as the floor for marks', () => {
    const paper = composePaper([{ id: 'x', type: 'mcq', prompt: 'x?', marks: 0 }], { targetMarks: 10 })
    expect(paper.totalMarks).toBe(1)
  })
})

describe('summarise', () => {
  it('counts the pool per section and reports what no section claims', () => {
    const withOrphan = [...POOL, q('w1', 'weird', 2, 'B4.9.9.9.9')]
    const summary = summarise(withOrphan)
    expect(summary.total).toBe(withOrphan.length)
    expect(summary.bySection.map((s) => s.count)).toEqual([8, 6, 3])
    expect(summary.unplaced).toBe(1)
    expect(summary.marks).toBe(withOrphan.reduce((sum, x) => sum + x.marks, 0))
  })
})

describe('sectionForType', () => {
  it('finds the section for a type, and nothing for a type the plan ignores', () => {
    expect(sectionForType('mcq', SECTION_PLAN).id).toBe('A')
    expect(sectionForType('essay', SECTION_PLAN).id).toBe('C')
    expect(sectionForType('matching', SECTION_PLAN)).toBe(null)
  })
})

describe('the term scope — a paper for the term, not the year', () => {
  // The schedule is the curriculum map's own answer to "what is taught in term 2".
  const LESSONS = [
    { term: 1, indicatorCode: 'B7.1.1.1.1', subStrandName: 'Number and Numeration Systems' },
    { term: 1, indicatorCode: 'B7.1.1.1.1', subStrandName: 'Number and Numeration Systems' },
    { term: 2, indicatorCode: 'B7.1.2.1.1', subStrandName: 'Number Operations' },
    { term: 2, indicatorCode: 'B7.2.1.1.1', subStrandName: 'Patterns and Relations' },
    { term: 3, indicatorCode: 'B7.4.1.1.1', subStrandName: 'Data and Probability' },
  ]

  it('collects the distinct indicators a term schedules', () => {
    expect([...termScope(LESSONS, 1)]).toEqual(['B7.1.1.1.1'])
    expect([...termScope(LESSONS, 2)].sort()).toEqual(['B7.1.2.1.1', 'B7.2.1.1.1'])
    expect(termScope(LESSONS, 3).size).toBe(1)
  })

  it("takes the whole year for 'all', and tolerates an empty schedule", () => {
    expect(termScope(LESSONS, 'all').size).toBe(4)
    expect(termScope([], 2).size).toBe(0)
    expect(termScope(undefined, 'all').size).toBe(0)
  })

  it('restricts a pool to the scope, reading both question shapes', () => {
    const pool = [
      { id: 'a', indicatorCode: 'B7.1.1.1.1' },
      // Firestore questions carry an array (`QuestionForm`/`starterToFirestore`).
      { id: 'b', indicatorCodes: ['B7.1.2.1.1'] },
      { id: 'c', indicatorCodes: ['B7.4.1.1.1'] },
      { id: 'd' },
    ]
    expect(filterByIndicators(pool, termScope(LESSONS, 2)).map((x) => x.id)).toEqual(['b'])
    expect(filterByIndicators(pool, termScope(LESSONS, 1)).map((x) => x.id)).toEqual(['a'])
    // An empty scope means "no restriction", not "nothing" — a subject-grade
    // with no schedule must not produce an empty paper.
    expect(filterByIndicators(pool, new Set()).map((x) => x.id)).toEqual(['a', 'b', 'c', 'd'])
  })

  it('reports which scheduled indicators nothing in the pool asks about', () => {
    const pool = [{ id: 'b', indicatorCodes: ['B7.1.2.1.1'] }]
    const cover = coverageOf(pool, termScope(LESSONS, 2))
    expect(cover.total).toBe(2)
    expect(cover.covered).toBe(1)
    expect(cover.percent).toBe(50)
    expect(cover.missing).toEqual(['B7.2.1.1.1'])
  })

  it('groups the gaps by sub-strand, counting each indicator once', () => {
    // The same code appears on five lessons (one a week); counting lessons
    // would report a gap five times its size.
    const weekly = Array.from({ length: 5 }, () => ({
      term: 2,
      indicatorCode: 'B7.2.1.1.1',
      subStrandName: 'Patterns and Relations',
    }))
    const groups = groupMissing([...LESSONS, ...weekly], ['B7.2.1.1.1', 'B7.9.9.9.9'])
    expect(groups).toContainEqual({ name: 'Patterns and Relations', count: 1 })
    // A missing code the schedule never mentions is still reported, by name.
    expect(groups).toContainEqual({ name: 'codes the schedule does not name', count: 1 })
  })

  it('says zero rather than NaN when there is no scope at all', () => {
    expect(coverageOf([], new Set())).toMatchObject({ total: 0, covered: 0, percent: 0, missing: [] })
  })
})

describe('indicatorOf', () => {
  it('reads the served bank string and the Firestore array alike', () => {
    expect(indicatorOf({ indicatorCode: 'B4.1.1.1.1' })).toBe('B4.1.1.1.1')
    expect(indicatorOf({ indicatorCodes: ['B4.1.1.1.2', 'B4.1.1.1.3'] })).toBe('B4.1.1.1.2')
    expect(indicatorOf({ indicatorCode: 'x', indicatorCodes: ['y'] })).toBe('x')
    expect(indicatorOf({})).toBe(null)
    expect(indicatorOf(undefined)).toBe(null)
  })
})

describe('buildPool', () => {
  it('keeps authored questions first and drops exact duplicates', () => {
    const owned = [q('m1', 'mcq', 1, 'B4.1.1.1.1')]
    const starter = [q('m1', 'mcq', 1, 'B4.1.1.1.1'), q('m2', 'mcq', 1, 'B4.1.1.1.2')]
    const pool = buildPool(owned, starter)
    expect(pool.map((x) => x.id)).toEqual(['m1', 'm2'])
  })

  it('keeps a starter question that a teacher has not imported', () => {
    const pool = buildPool([], [q('starter-1', 'mcq', 1, 'B4.1.1.1.1')])
    expect(pool.map((x) => x.id)).toEqual(['starter-1'])
  })
})
