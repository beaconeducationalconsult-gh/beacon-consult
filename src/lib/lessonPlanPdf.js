import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { gradeLabel } from './grades'

const PHASES = [
  ['starter', 'Starter / Introduction'],
  ['main', 'Main Activities (Development)'],
  ['plenary', 'Plenary / Conclusion'],
]

/** Lesson plan → PDF (client-side, A4 portrait), matching the Word export. */
export function buildLessonPlanPdf(plan, { school, teacher } = {}) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const margin = 40
  const width = doc.internal.pageSize.getWidth() - margin * 2
  let y = 48

  doc.setFontSize(16)
  doc.setTextColor('#4F46E5')
  doc.text('Lesson Plan', margin, y)
  y += 20
  doc.setFontSize(11)
  doc.setTextColor('#64748B')
  doc.text(
    [plan.subjectName || plan.subjectId, gradeLabel(plan.grade), plan.week ? `Week ${plan.week}` : null]
      .filter(Boolean)
      .join(' · '),
    margin,
    y
  )
  y += 24

  const details = [
    school && ['School', school],
    teacher && ['Teacher', teacher],
    ['Term / Week', `Term ${plan.term || '—'} / Week ${plan.week || '—'}`],
    ['Duration', `${plan.durationMinutes || 60} minutes`],
    ['Indicator', (plan.indicatorCodes || [])[0] || plan.indicatorCode],
    ['Strand', plan.strandName],
    ['Content standard', plan.contentStandard],
  ].filter((row) => row && row[1])

  autoTable(doc, {
    startY: y,
    body: details.map(([label, value]) => [label, String(value)]),
    theme: 'grid',
    styles: { fontSize: 9, cellPadding: 4 },
    columnStyles: { 0: { cellWidth: 110, fontStyle: 'bold', fillColor: '#F8FAFC' } },
    margin: { left: margin, right: margin },
  })
  y = doc.lastAutoTable.finalY + 20

  const section = (heading, lines) => {
    if (!lines?.length) return
    doc.setFontSize(11)
    doc.setTextColor('#4F46E5')
    doc.text(heading, margin, y)
    y += 14
    doc.setFontSize(9)
    doc.setTextColor('#334155')
    for (const line of lines) {
      const wrapped = doc.splitTextToSize(String(line), width - 10)
      doc.text(wrapped, margin + 6, y)
      y += wrapped.length * 12 + 4
    }
    y += 8
  }

  const objectives = plan.objectives?.length
    ? plan.objectives
    : [plan.performanceIndicator || plan.indicatorDescription].filter(Boolean)
  section('Learning Objectives', objectives.map((o) => `• ${o}`))
  if (plan.keywords?.length) section('Key Words', [plan.keywords.join(' · ')])
  if (plan.rpk) section("Relevant Previous Knowledge", [plan.rpk])
  for (const [key, label] of PHASES) {
    if (plan[key]?.length) section(label, plan[key].map((item, i) => `${i + 1}. ${item}`))
  }
  if (plan.competencies?.length) section('Core Competencies', [[].concat(plan.competencies).join('; ')])
  if (plan.resources?.length) section('Teaching & Learning Materials', [[].concat(plan.resources).join('; ')])
  if (plan.assessment) section('Assessment', [plan.assessment])
  if (plan.differentiation) section('Differentiation / Support', [plan.differentiation])

  autoTable(doc, {
    startY: y + 10,
    head: [['Signature', 'Name', 'Date']],
    body: [
      ['Teacher', teacher || '', ''],
      ['Head teacher', '', ''],
    ],
    theme: 'grid',
    styles: { fontSize: 9, cellPadding: 8 },
    headStyles: { fillColor: '#F1F5F9', textColor: '#334155' },
    columnStyles: { 0: { cellWidth: 110 }, 1: { cellWidth: 220 } },
    margin: { left: margin, right: margin },
  })

  doc.setFontSize(8)
  doc.setTextColor('#94A3B8')
  doc.text('Generated with Beacon Educational Consult', margin, doc.internal.pageSize.getHeight() - 24)

  return doc
}

/** Lesson plan → PDF download (client-side). */
export function downloadLessonPlanPdf(plan, meta = {}) {
  buildLessonPlanPdf(plan, meta).save(`Lesson_Plan_${plan.subjectId}_${plan.grade}_W${plan.week || 1}.pdf`)
}
