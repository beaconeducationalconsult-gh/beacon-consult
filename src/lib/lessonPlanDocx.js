import { Document, Packer, Paragraph } from 'docx'
import {
  H2,
  bullet,
  step,
  para,
  fill,
  metaLine,
  referenceTable,
  titleBlock,
  documentStyles,
  brandedFooter,
  signatureLines,
} from './docxShared'
import { gradeLabel } from './grades'

const PHASES = [
  { key: 'starter', title: 'Starter / Introduction' },
  { key: 'main', title: 'Main Activities (Development)' },
  { key: 'plenary', title: 'Plenary / Conclusion' },
]

/** `heading: H2` is a real heading level, so Word shows an outline and bold. */
const heading = (text) => new Paragraph({ text, heading: H2 })

/**
 * Lesson plan → .docx  (client-side, no server)
 *
 * Prints every phase the dataset carries — the portal's whole value is that it
 * matches the printed books, not that it is shorter than them.
 *
 * Laid out as a document a teacher hands in: title block, the fields they fill
 * in by hand, the curriculum reference they are answerable to, then the lesson
 * itself in numbered teaching order.
 */
export async function downloadLessonPlanDocx(plan, { school, teacher } = {}) {
  const key = plan.indicatorCodes?.[0] || plan.indicatorCode || ''
  const subject = plan.subjectName || plan.subjectId || ''

  const children = [
    ...titleBlock(
      'LESSON PLAN',
      [
        subject.toUpperCase(),
        gradeLabel(plan.grade).toUpperCase(),
        plan.term ? `TERM ${plan.term}` : null,
        plan.week ? `WEEK ${plan.week}` : null,
      ]
        .filter(Boolean)
        .join('  ·  ')
    ),
    metaLine([
      ['School', fill(school)],
      ['Teacher', fill(teacher)],
    ]),
    metaLine([
      ['Class', fill(null, 14)],
      ['Date', fill(null, 16)],
    ]),
    metaLine([
      ['Term / Week', `Term ${plan.term || '—'} / Week ${plan.week || '—'}`],
      ['Duration', `${plan.durationMinutes || 60} minutes`],
    ]),
  ]

  // The curriculum the lesson is answerable to, as a label/value table: a
  // content standard runs to two lines and needs its own column.
  const reference = [
    [key && 'Indicator', key],
    [plan.strandName && 'Strand', plan.strandName],
    [plan.subStrandName && 'Sub-strand', plan.subStrandName],
    [plan.contentStandard && 'Content standard', plan.contentStandard],
    [plan.indicatorDescription && 'Indicator text', plan.indicatorDescription],
    [plan.performanceIndicator && 'Performance indicator', plan.performanceIndicator],
  ].filter((row) => row[0])
  if (reference.length) {
    children.push(heading('Curriculum Reference'), referenceTable(reference))
  }

  children.push(heading('Learning Objectives'))
  const objectives = plan.objectives?.length
    ? plan.objectives
    : [plan.performanceIndicator || plan.indicatorDescription].filter(Boolean)
  if (objectives.length) {
    objectives.forEach((o) => children.push(bullet(o)))
  } else {
    children.push(para('By the end of the lesson, learners will be able to…', { italics: true }))
  }

  if (plan.keywords?.length) {
    children.push(heading('Key Words'), para([].concat(plan.keywords).join('  ·  ')))
  }

  if (plan.rpk) {
    children.push(heading("Relevant Previous Knowledge (Let's Remember)"), para(plan.rpk))
  }

  // Numbered, because a lesson is taught in order — and the numbers are text,
  // so a teacher who edits the document cannot end up with a list that
  // renumbers itself behind their back.
  for (const phase of PHASES) {
    const items = plan[phase.key]
    if (!items?.length) continue
    children.push(heading(phase.title))
    items.forEach((item, index) => children.push(step(index + 1, item)))
  }

  if (plan.competencies?.length) {
    children.push(heading('Core Competencies'), para([].concat(plan.competencies).join('; ')))
  }

  if (plan.resources?.length) {
    children.push(heading('Teaching & Learning Materials'), para([].concat(plan.resources).join('; ')))
  }

  if (plan.assessment) {
    children.push(heading('Assessment'), para(plan.assessment))
  }

  if (plan.differentiation) {
    children.push(heading('Differentiation / Support'), para(plan.differentiation))
  }

  children.push(
    heading('Sign Off'),
    ...signatureLines([
      ['Teacher', teacher || ''],
      ['Head teacher', ''],
    ])
  )

  const doc = new Document({
    creator: 'Beacon Educational Consult',
    title: `Lesson Plan — ${subject} ${plan.grade}`,
    description: key ? `Lesson plan for indicator ${key}` : undefined,
    styles: documentStyles(),
    sections: [
      {
        properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
        footers: { default: brandedFooter() },
        children,
      },
    ],
  })

  return Packer.toBlob(doc)
}
