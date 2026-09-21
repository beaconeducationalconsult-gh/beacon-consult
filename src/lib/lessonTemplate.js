/*
 * Which lesson-plan sections come from the syllabus teaching template rather
 * than from someone writing about this lesson (P1-4).
 *
 * `scripts/audit/audit_d_l2_template.py` measured every field of L2 across the
 * 13,140 slots (`data/audit/l2_template.json`): `starter` has a median of 156
 * distinct values inside a subject-grade's 180 slots and `main` 60 — that is
 * per-lesson content. `rpk` is a single value in 70 of 73 subject-grades,
 * `plenary` in 60, `assessment` and `competencies` in 67 — those are the printed
 * teaching template, repeated for every lesson of the subject.
 *
 * The distinction matters to whoever reads a plan: a section inherited word for
 * word from the syllabus should not look like something the teacher wrote. A
 * plan filled from the curriculum records which of its sections were inherited,
 * and the exports say so next to the heading.
 */

/** The fields the measurement found to be subject-wide templates. */
export const ROUTINE_FIELDS = [
  'keywords', 'rpk', 'competencies', 'resources', 'plenary', 'assessment',
]

/** How each field is titled in the exported document. */
export const FIELD_TITLES = {
  starter: 'Starter / Introduction',
  main: 'Main Activities (Development)',
  plenary: 'Plenary / Conclusion',
  rpk: "Relevant Previous Knowledge",
  competencies: 'Core Competencies',
  resources: 'Teaching & Learning Materials',
  keywords: 'Key Words',
  assessment: 'Assessment',
}

// Below this many slots, "one value everywhere" says nothing — a subject with
// three scheduled lessons is not evidence of a template.
const MIN_SLOTS = 5

const valueOf = (value) => (Array.isArray(value) ? value.join('\n') : String(value ?? ''))

/**
 * The routine fields this subject-grade repeats unchanged: one non-empty value
 * across every one of its scheduled lessons.
 */
export function templateFields(lessons) {
  if (!Array.isArray(lessons) || lessons.length < MIN_SLOTS) return []
  return ROUTINE_FIELDS.filter((field) => {
    const values = new Set(
      lessons.map((lesson) => valueOf(lesson?.[field])).filter((value) => value !== '')
    )
    return values.size === 1
  })
}

/** A sentence naming the sections, for a toast or a footnote. */
export function templateNote(fields) {
  const titles = (fields || []).map((field) => FIELD_TITLES[field]).filter(Boolean)
  if (!titles.length) return ''
  const list = titles.length > 1 ? `${titles.slice(0, -1).join(', ')} and ${titles.at(-1)}` : titles[0]
  return `${list} ${titles.length > 1 ? 'are' : 'is'} the subject's teaching template from the ` +
    `curriculum${titles.length > 1 ? ' — the same for every lesson of ' : ' — '}this subject, not ` +
    `written for this lesson.`
}

/** Heading text for an export: the section title, marked when it is inherited. */
export function headingWithProvenance(field, title, templatedFields) {
  return (templatedFields || []).includes(field) ? `${title} (teaching template)` : title
}
