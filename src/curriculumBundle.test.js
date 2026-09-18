import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { buildTree } from './hooks/useCurriculum'

/**
 * Contract tests over the *real* committed bundle in public/curriculum.
 *
 * The portal once rendered an empty curriculum browser because a grade id was
 * looked up as a subject id — the data was fine, nothing checked the join. These
 * assertions encode the relationships the UI assumes, so a broken or rebuilt
 * bundle fails here rather than in front of a teacher.
 */
const read = (name) => JSON.parse(readFileSync(new URL(`../public/curriculum/${name}`, import.meta.url), 'utf8'))

const grades = read('grades.json')
const ids = grades.map((g) => g.id)
const bundle = new Map(
  ids.map((id) => {
    const key = id.toLowerCase()
    return [id, { subjects: read(`${key}_subjects.json`), indicators: read(`${key}_indicators.json`) }]
  })
)

const flatten = (tree) =>
  tree.flatMap((s) => s.subStrands.flatMap((sub) => sub.standards.flatMap((std) => std.indicators)))

describe('the grade list', () => {
  it('covers KG1 to B9', () => {
    expect(ids).toEqual(['KG1', 'KG2', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9'])
  })

  it('has a subjects and an indicators file for every grade', () => {
    for (const [grade, { subjects, indicators }] of bundle) {
      expect(Array.isArray(subjects), `${grade} subjects`).toBe(true)
      expect(Array.isArray(indicators), `${grade} indicators`).toBe(true)
      expect(subjects.length, `${grade} has subjects`).toBeGreaterThan(0)
      expect(indicators.length, `${grade} has indicators`).toBeGreaterThan(0)
    }
  })
})

describe.each(ids)('%s', (grade) => {
  const { subjects, indicators } = bundle.get(grade)
  const subjectIds = subjects.map((s) => s.id)
  const indicatorSubjects = new Set(indicators.map((i) => i.subjectId))

  it('gives every subject an id and a name', () => {
    for (const subject of subjects) {
      expect(subject.id, `${grade} subject id`).toBeTruthy()
      expect(subject.name, `${grade}/${subject.id} name`).toBeTruthy()
    }
  })

  // The join the whole browser hangs off: subject ids in the subjects file must
  // be the subjectId stamped on indicators. An orphan means a subject that can
  // never show any indicators.
  it('joins subjects to indicators in both directions', () => {
    const orphans = [...indicatorSubjects].filter((id) => !subjectIds.includes(id))
    expect(orphans, `${grade} indicators with no matching subject`).toEqual([])

    const empty = subjectIds.filter((id) => !indicatorSubjects.has(id))
    expect(empty, `${grade} subjects with no indicators`).toEqual([])
  })

  it('stamps the grade on every indicator', () => {
    const wrong = indicators.filter((i) => i.grade !== grade)
    expect(wrong.length, `${grade} indicators stamped with another grade`).toBe(0)
  })

  // `id` is namespaced (`mathematics_B4.1.1.1.1`) and is what
  // validate_app_curriculum.py checks. It is the key lesson plans store.
  it('keeps indicator ids unique within the grade', () => {
    const seen = new Set()
    const duplicates = new Set()
    for (const { id } of indicators) {
      if (seen.has(id)) duplicates.add(id)
      seen.add(id)
    }
    expect([...duplicates], `${grade} duplicate indicator ids`).toEqual([])
  })

  // `code` carries no subject namespace — `B4.1.1.1.1` exists in all ten B4
  // subjects — so uniqueness only holds per subject-grade. Anything keyed on a
  // bare code has to be scoped by subject (or use `id`).
  it('keeps indicator codes unique within a subject, not across the grade', () => {
    for (const subjectId of new Set(indicators.map((i) => i.subjectId))) {
      const codes = indicators.filter((i) => i.subjectId === subjectId).map((i) => i.code)
      const duplicates = codes.filter((code, index) => codes.indexOf(code) !== index)
      expect([...new Set(duplicates)], `${grade}/${subjectId} duplicate codes`).toEqual([])
    }
  })

  it('carries the numbers the UI sorts by', () => {
    for (const indicator of indicators) {
      expect(typeof indicator.strandNumber, `${grade}/${indicator.code} strandNumber`).toBe('number')
      expect(typeof indicator.subStrandNumber, `${grade}/${indicator.code} subStrandNumber`).toBe('number')
      expect(indicator.contentStandardCode || indicator.code, `${grade}/${indicator.code} standard`).toBeTruthy()
    }
  })

  it('builds a non-empty tree for every subject, losing nothing', () => {
    for (const subjectId of subjectIds) {
      const expected = indicators.filter((i) => i.subjectId === subjectId)
      const tree = buildTree(indicators, subjectId)

      expect(tree.length, `${grade}/${subjectId} strands`).toBeGreaterThan(0)
      expect(flatten(tree).length, `${grade}/${subjectId} indicators kept`).toBe(expected.length)

      // every indicator keeps its identity through the nesting
      const kept = flatten(tree).map((i) => i.id).sort()
      expect(kept).toEqual(expected.map((i) => i.id).sort())
    }
  })
})

describe('known gaps stay known', () => {
  it('has no schedules file for the kindergarten grades', () => {
    const kg = grades.filter((g) => g.id.startsWith('KG'))
    for (const grade of kg) expect(grade.hasSchedules).toEqual([])

    // and that is a deliberate gap, not a missing build: every other grade has one
    for (const grade of grades.filter((g) => !g.id.startsWith('KG'))) {
      expect(grade.hasSchedules.length, `${grade.id} schedules`).toBeGreaterThan(0)
    }
  })
})
