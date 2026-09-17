import { Document, Packer, Paragraph } from 'docx'
import { H2, para, bullet, table, titleBlock, brandedFooter, labelValue, BRAND } from './docxShared'
import { gradeLabel } from './grades'

const PHASES = [
  { key: 'starter', title: 'Starter / Introduction' },
  { key: 'main', title: 'Main Activities (Development)' },
  { key: 'plenary', title: 'Plenary / Conclusion' },
]

/**
 * Lesson plan → .docx  (client-side, no server)
 *
 * Prints every phase the dataset carries — the portal's whole value is that it
 * matches the printed books, not that it is shorter than them.
 */
export async function downloadLessonPlanDocx(plan, { school, teacher } = {}) {
  const key = plan.indicatorCodes?.[0] || plan.indicatorCode || ''
  const children = [
    ...titleBlock(
      'Lesson Plan',
      [plan.subjectName || plan.subjectId, gradeLabel(plan.grade), plan.week ? `Week ${plan.week}` : null]
        .filter(Boolean)
        .join(' · ')
    ),
    ...(school ? [labelValue('School', school)] : []),
    ...(teacher ? [labelValue('Teacher', teacher)] : []),
    labelValue('Term / Week', `Term ${plan.term || '—'} / Week ${plan.week || '—'}`),
    labelValue('Duration', `${plan.durationMinutes || 60} minutes`),
    para(''),
  ]

  if (key || plan.indicatorDescription) {
    children.push(new Paragraph({ text: 'Curriculum Reference', heading: H2 }))
    if (key) children.push(labelValue('Indicator', key))
    if (plan.strandName) children.push(labelValue('Strand', plan.strandName))
    if (plan.subStrandName) children.push(labelValue('Sub-strand', plan.subStrandName))
    if (plan.contentStandard) children.push(labelValue('Content Standard', plan.contentStandard))
    if (plan.indicatorDescription) children.push(labelValue('Indicator text', plan.indicatorDescription))
    if (plan.performanceIndicator) children.push(labelValue('Performance indicator', plan.performanceIndicator))
    children.push(para(''))
  }

  children.push(new Paragraph({ text: 'Learning Objectives', heading: H2 }))
  const objectives = plan.objectives?.length
    ? plan.objectives
    : [plan.performanceIndicator || plan.indicatorDescription].filter(Boolean)
  if (objectives.length) {
    objectives.forEach((o) => children.push(bullet(o)))
  } else {
    children.push(para('By the end of the lesson, learners will be able to…'))
  }
  children.push(para(''))

  if (plan.keywords?.length) {
    children.push(new Paragraph({ text: 'Key Words', heading: H2 }))
    children.push(para(plan.keywords.join(' · ')))
    children.push(para(''))
  }

  if (plan.rpk) {
    children.push(new Paragraph({ text: "Relevant Previous Knowledge (Let's remember)", heading: H2 }))
    children.push(para(plan.rpk))
    children.push(para(''))
  }

  for (const phase of PHASES) {
    const items = plan[phase.key]
    if (!items?.length) continue
    children.push(new Paragraph({ text: phase.title, heading: H2 }))
    items.forEach((item, index) => children.push(bullet(item, 0), para(`   ⏱ ${index + 1}`, { size: 18 })))
    children.push(para(''))
  }

  if (plan.competencies?.length) {
    children.push(new Paragraph({ text: 'Core Competencies', heading: H2 }))
    children.push(para([].concat(plan.competencies).join('; ')))
    children.push(para(''))
  }

  if (plan.resources?.length) {
    children.push(new Paragraph({ text: 'Teaching & Learning Materials', heading: H2 }))
    children.push(para([].concat(plan.resources).join('; ')))
    children.push(para(''))
  }

  if (plan.assessment) {
    children.push(new Paragraph({ text: 'Assessment', heading: H2 }))
    children.push(para(plan.assessment))
    children.push(para(''))
  }

  if (plan.differentiation) {
    children.push(new Paragraph({ text: 'Differentiation / Support', heading: H2 }))
    children.push(para(plan.differentiation))
    children.push(para(''))
  }

  children.push(
    table(
      ['Signature', 'Name', 'Date'],
      [['Teacher', teacher || '', ''], ['Head teacher', '', '']],
      [25, 45, 30]
    )
  )
  children.push(brandedFooter())

  const doc = new Document({
    creator: BRAND.name,
    title: `Lesson Plan — ${plan.subjectName || plan.subjectId} ${plan.grade}`,
    sections: [{ children }],
  })

  return Packer.toBlob(doc)
}
