/*
 * The teaching models (P3-4).
 *
 * Five interactive models — not fifty — for one subject-grade, so the question
 * "does a screen actually help here" can be answered before anyone invests in a
 * library of them. Each entry names the served indicators it teaches, and
 * `modelsFor()` attaches those indicators' own wording from the bundle, so what
 * is on screen is always the curriculum the teacher is working from, not a
 * paraphrase of it.
 *
 * The catalogue is data, the components are code (`src/components/models/`), and
 * `src/teachingModels.test.js` checks that every entry names indicators that are
 * really served for that subject and grade — a model for an indicator that does
 * not exist would be a demo, not teaching material.
 */

/** The pilot: one subject-grade, worked through properly. */
export const PILOT = { subjectId: 'mathematics', grade: 'B4' }

export const TEACHING_MODELS = [
  {
    id: 'place-value',
    title: 'Place value frame',
    blurb: 'Set a digit in each column; the expanded form and the number in words follow.',
    component: 'place-value',
    subjectId: 'mathematics',
    grade: 'B4',
    indicatorCodes: ['B4.1.1.1.1', 'B4.1.1.1.2'],
  },
  {
    id: 'number-line',
    title: 'Compare, order and round',
    blurb: 'Two markers on a number line; the comparison sentence and both roundings appear.',
    component: 'number-line',
    subjectId: 'mathematics',
    grade: 'B4',
    indicatorCodes: ['B4.1.1.1.4', 'B4.1.1.1.5'],
  },
  {
    id: 'fraction-strips',
    title: 'Fraction strips',
    blurb: 'Cut two strips differently, shade the same amount — equivalent fractions you can see.',
    component: 'fraction-strips',
    subjectId: 'mathematics',
    grade: 'B4',
    indicatorCodes: ['B4.1.3.1.2', 'B4.1.3.2.1'],
  },
  {
    id: 'factor-arrays',
    title: 'Factor arrays',
    blurb: 'Arrange counters into every rectangle that uses them all: factors, primes, squares.',
    component: 'factor-arrays',
    subjectId: 'mathematics',
    grade: 'B4',
    indicatorCodes: ['B4.1.1.3.1', 'B4.1.1.3.6'],
  },
  {
    id: 'area-perimeter',
    title: 'Perimeter and area',
    blurb: 'Resize a rectangle; count the squares and the fence, then find every shape with the same fence.',
    component: 'area-perimeter',
    subjectId: 'mathematics',
    grade: 'B4',
    indicatorCodes: ['B4.3.3.1.3', 'B4.3.3.1.4', 'B4.3.3.2.1'],
  },
]

/** The models that exist for a subject-grade. */
export function modelsFor(subjectId, grade) {
  return TEACHING_MODELS.filter((model) => model.subjectId === subjectId && model.grade === grade)
}

/** The subject-grades that have models, for a picker. */
export function modelledSubjectGrades() {
  return [...new Set(TEACHING_MODELS.map((model) => `${model.subjectId}|${model.grade}`))]
    .map((key) => {
      const [subjectId, grade] = key.split('|')
      return { subjectId, grade }
    })
}

/** Attach each indicator's own text from the served bundle. */
export function attachIndicators(model, indicators) {
  return {
    ...model,
    indicators: model.indicatorCodes.map((code) => {
      const found = (indicators || []).find((row) => row.code === code)
      return {
        code,
        description: found?.description || '',
        strandName: found?.strandName || '',
        contentStandard: found?.contentStandardDescription || '',
        served: Boolean(found),
      }
    }),
  }
}
