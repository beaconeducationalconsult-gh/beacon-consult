import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import {
  ROUTINE_FIELDS, headingWithProvenance, templateFields, templateNote,
} from './lessonTemplate'

/*
 * P1-4. The honest description of L2 ("per-lesson starter/main content inside a
 * subject-wide routine template") has to reach the plan a teacher prints, so
 * these tests hold both halves: the measurement that decides what counts as a
 * template, and the labels the form and the exports put on it.
 */

// A subject-grade whose routine fields are constant and whose content is not —
// the shape data/audit/l2_template.json found in 60 of 73 subject-grades.
const slot = (over = {}) => ({
  rpk: 'Learners used number charts in Basic 3.',
  plenary: ['Quick-fire oral quiz on today’s skill.'],
  assessment: 'Observe group work; mark the exercise.',
  competencies: ['Critical Thinking and Problem Solving', 'Communication and Collaboration'],
  resources: ['NaCCA approved textbook', 'TLMs'],
  keywords: ['mathematics', 'b4', 'ccp'],
  starter: ['Recap place value with a chart.'],
  main: ['Work through the example on the board.'],
  ...over,
})

const lessons = Array.from({ length: 12 }, (_, i) => slot({
  starter: [`Starter ${i}`],
  main: [`Main ${i}`],
}))

describe('which fields are the subject’s template', () => {
  it('names the routine fields when they repeat across the year', () => {
    expect(templateFields(lessons)).toEqual(['keywords', 'rpk', 'competencies', 'resources', 'plenary', 'assessment'])
  })

  it('leaves out a field that varies — that is content, not template', () => {
    const varied = lessons.map((lesson, i) => ({ ...lesson, plenary: [`Plenary ${i}`] }))
    expect(templateFields(varied)).not.toContain('plenary')
    expect(templateFields(varied)).toContain('rpk')
  })

  it('treats a list and its joined text as the same value', () => {
    const asText = lessons.map((lesson) => ({ ...lesson, competencies: 'Critical Thinking and Problem Solving; Communication and Collaboration' }))
    expect(templateFields(asText)).toContain('competencies')
  })

  it('says nothing about a subject with almost no lessons', () => {
    expect(templateFields(lessons.slice(0, 3))).toEqual([])
    expect(templateFields(null)).toEqual([])
  })

  it('ignores empty values when deciding', () => {
    const sparse = lessons.map((lesson) => ({ ...lesson, rpk: '' }))
    expect(templateFields(sparse)).not.toContain('rpk')
  })
})

describe('saying it out loud', () => {
  it('names the sections in a sentence', () => {
    const note = templateNote(['rpk', 'plenary'])
    expect(note).toContain('Relevant Previous Knowledge')
    expect(note).toContain('Plenary / Conclusion')
    expect(note).toContain("teaching template")
    expect(templateNote([])).toBe('')
  })

  it('marks only the inherited headings', () => {
    expect(headingWithProvenance('rpk', "Relevant Previous Knowledge", ['rpk']))
      .toBe("Relevant Previous Knowledge (teaching template)")
    expect(headingWithProvenance('starter', 'Starter / Introduction', ['rpk']))
      .toBe('Starter / Introduction')
    expect(headingWithProvenance('main', 'Main Activities', undefined)).toBe('Main Activities')
  })
})

describe('the measurement the app relies on matches the audit artifact', () => {
  const audit = JSON.parse(readFileSync(new URL('../../data/audit/l2_template.json', import.meta.url), 'utf8'))

  it('measured 13,140 slots and found the same routine fields', () => {
    expect(audit.slots).toBe(13140)
    const routine = Object.entries(audit.summary).filter(([, row]) => row.routine).map(([field]) => field)
    expect(new Set(routine)).toEqual(new Set(['competencies', 'resources', 'keywords', 'rpk', 'plenary', 'assessment']))
  })

  it('found the content fields varying, not constant', () => {
    for (const field of ['starter', 'main', 'ind_desc', 'perf_indicator']) {
      expect(audit.summary[field].constantIn, field).toBe(0)
      expect(audit.summary[field].medianDistinct, field).toBeGreaterThan(5)
    }
  })

  it('keeps the app’s routine list identical to the artifact’s', () => {
    const routine = Object.entries(audit.summary).filter(([, row]) => row.routine).map(([field]) => field).sort()
    expect([...ROUTINE_FIELDS].sort()).toEqual(routine)
  })
})
