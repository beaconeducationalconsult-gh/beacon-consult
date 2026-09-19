import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { gradeLabel } from './grades'

/**
 * Printable exam paper from a question selection (PDF, client-side).
 * Two-column MCQs, then short/essay with working space, then the marking scheme.
 */
export function buildQuestionPaper(
  questions,
  { subjectName, grade, term, totalMarks, school, durationMinutes = 120, includeAnswers = true } = {}
) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const margin = 44
  const width = doc.internal.pageSize.getWidth() - margin * 2
  let y = 52

  doc.setFontSize(15)
  doc.setTextColor('#111827')
  doc.text(school || 'Beacon Educational Consult', margin, y, { maxWidth: width })
  y += 20
  doc.setFontSize(12)
  doc.setTextColor('#4F46E5')
  doc.text(`${subjectName || 'Subject'} — end of term examination`, margin, y)
  y += 18
  doc.setFontSize(10)
  doc.setTextColor('#475569')
  doc.text(
    `${gradeLabel(grade)} · Term ${term} · Duration ${durationMinutes} minutes · Total marks ${totalMarks ?? '—'}`,
    margin,
    y
  )
  y += 16
  doc.text('Name: ______________________________    Class: ____________    Index no: ____________', margin, y)
  y += 22

  doc.setDrawColor('#E2E8F0')
  doc.line(margin, y, margin + width, y)
  y += 20

  const mcq = questions.filter((q) => q.type === 'mcq')
  const written = questions.filter((q) => q.type !== 'mcq')

  if (mcq.length) {
    doc.setFontSize(11)
    doc.setTextColor('#111827')
    doc.text('SECTION A — Multiple choice', margin, y)
    y += 14
    autoTable(doc, {
      startY: y,
      body: mcq.map((q, index) => [
        `${index + 1}. ${q.prompt || q.question || ''}`,
        (q.options || []).map((opt, i) => `${String.fromCharCode(65 + i)}. ${opt}`).join('\n'),
        `${q.marks ?? 1}`,
      ]),
      theme: 'plain',
      styles: { fontSize: 9, cellPadding: 5, valign: 'top' },
      columnStyles: { 0: { cellWidth: width * 0.45 }, 1: { cellWidth: width * 0.45 }, 2: { cellWidth: 30, halign: 'right' } },
      margin: { left: margin, right: margin },
    })
    y = doc.lastAutoTable.finalY + 22
  }

  if (written.length) {
    doc.setFontSize(11)
    doc.setTextColor('#111827')
    doc.text('SECTION B — Written questions', margin, y)
    y += 8
    autoTable(doc, {
      startY: y,
      head: [['#', 'Question', 'Marks']],
      body: written.map((q, index) => [
        `${mcq.length + index + 1}`,
        q.prompt || q.question || '',
        `${q.marks ?? 5}`,
      ]),
      theme: 'grid',
      styles: { fontSize: 9, cellPadding: 6, valign: 'top' },
      headStyles: { fillColor: '#4F46E5', textColor: '#FFFFFF' },
      columnStyles: { 0: { cellWidth: 26 }, 1: { cellWidth: width - 76 }, 2: { cellWidth: 50, halign: 'right' } },
      margin: { left: margin, right: margin },
    })
    y = doc.lastAutoTable.finalY + 30
    doc.setFontSize(9)
    doc.setTextColor('#64748B')
    doc.text('Answer all questions in the spaces provided.', margin, y)
  }

  if (includeAnswers) {
    const answers = questions.filter((q) => q.answer)
    if (answers.length) {
      doc.addPage()
      let ay = 52
      doc.setFontSize(13)
      doc.setTextColor('#4F46E5')
      doc.text('Marking scheme (teacher copy)', margin, ay)
      ay += 18
      autoTable(doc, {
        startY: ay,
        head: [['#', 'Question', 'Answer', 'Marks']],
        body: answers.map((q, index) => [
          `${index + 1}`,
          q.prompt || q.question || '',
          q.answer,
          `${q.marks ?? 1}`,
        ]),
        theme: 'grid',
        styles: { fontSize: 8, cellPadding: 5, valign: 'top' },
        headStyles: { fillColor: '#F1F5F9', textColor: '#334155' },
        columnStyles: {
          0: { cellWidth: 24 },
          1: { cellWidth: width * 0.32 },
          2: { cellWidth: width * 0.5 },
          3: { cellWidth: 42, halign: 'right' },
        },
        margin: { left: margin, right: margin },
      })
    }
  }

  doc.setFontSize(8)
  doc.setTextColor('#94A3B8')
  doc.text('Generated with Beacon Educational Consult', margin, doc.internal.pageSize.getHeight() - 24)

  return doc
}

/** Question selection → printable paper (PDF download). */
export function downloadQuestionPaper(questions, options = {}) {
  const { subjectName, grade, term } = options
  // Every option is forwarded — the callers pass totalMarks, and dropping it
  // would print "Total marks —" on a real paper.
  buildQuestionPaper(questions, options).save(
    `Exam_${subjectName || 'paper'}_${grade}_T${term}.pdf`
  )
}
