import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { BECE_FORMAT } from './becePaper'

/*
 * The BECE mock, printed.
 *
 * `questionPaper.js` prints the term paper the exam builder composes — one
 * objective section, one written section. A BECE paper is a different print:
 * two papers at one sitting, a rubric that says "answer four", and questions
 * with lettered parts whose marks read down the margin. This keeps that shape
 * honest instead of bending the term-paper printer to it, in the same house
 * style (jsPDF + autoTable, A4 portrait, the brand headings, the footer).
 *
 * Like every exporter here it splits at the document: `buildBecePaper` returns
 * it, `downloadBecePaper` saves it — the seam the tests use.
 */
export function buildBecePaper(
  paper,
  { school, subjectName = 'Mathematics', includeAnswers = true } = {}
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
  doc.text(`BECE Mock Examination — ${subjectName} (Common Core, B7–B9)`, margin, y)
  y += 16
  doc.setFontSize(10)
  doc.setTextColor('#475569')
  doc.text(
    `Paper 1: Objective — ${BECE_FORMAT.paper1.count} questions, ${paper.paper1.minutes} minutes, ${paper.paper1.marks} marks   ·   `
    + `Paper 2: Essay — answer ${paper.paper2.answerCount} of ${paper.paper2.questions.length}, ${paper.paper2.minutes} minutes, ${paper.paper2.marks} marks`,
    margin, y, { maxWidth: width }
  )
  y += 14
  doc.text(`Total: ${paper.totalMarks} marks · one sitting`, margin, y)
  y += 16
  doc.setFontSize(10)
  doc.text('Name: ______________________________    Class: ____________    Index no: ____________', margin, y)
  y += 18
  doc.setDrawColor('#E2E8F0')
  doc.line(margin, y, margin + width, y)
  y += 20

  /* ── Paper 1 ────────────────────────────────────────────────────────────── */
  doc.setFontSize(11)
  doc.setTextColor('#111827')
  doc.text(`PAPER 1 — OBJECTIVE  (${paper.paper1.marks} marks, ${paper.paper1.minutes} minutes)`, margin, y)
  y += 14
  doc.setFontSize(9)
  doc.setTextColor('#64748B')
  doc.text('Answer ALL the questions. Each question carries 1 mark.', margin, y)
  y += 12

  autoTable(doc, {
    startY: y,
    body: paper.paper1.questions.map((question, index) => [
      `${index + 1}. ${question.prompt || question.question || ''}`,
      (question.options || []).map((opt, i) => `${String.fromCharCode(65 + i)}. ${opt}`).join('\n'),
    ]),
    theme: 'plain',
    styles: { fontSize: 9, cellPadding: 5, valign: 'top' },
    columnStyles: { 0: { cellWidth: width * 0.52 }, 1: { cellWidth: width * 0.48 } },
    margin: { left: margin, right: margin },
  })
  doc.addPage()
  y = 52

  /* ── Paper 2 ────────────────────────────────────────────────────────────── */
  doc.setFontSize(11)
  doc.setTextColor('#111827')
  doc.text(`PAPER 2 — ESSAY  (${paper.paper2.marks} marks, ${paper.paper2.minutes} minutes)`, margin, y)
  y += 14
  doc.setFontSize(9)
  doc.setTextColor('#64748B')
  doc.text(
    `Answer ${paper.paper2.answerCount} questions only. Each question carries ${BECE_FORMAT.paper2.marksEach} marks.`
    + ' Show all your working.',
    margin, y
  )
  y += 14

  autoTable(doc, {
    startY: y,
    body: paper.paper2.questions.map((question) => ([
      [
        {
          content: `Question ${question.number}   (${question.marks} marks)`,
          styles: { fontStyle: 'bold', fontSize: 10 },
        },
      ],
      ...question.parts.map((part) => ([
        `(${part.letter}) ${part.question.prompt || part.question.question || ''}`,
        `${part.marks} mark${part.marks === 1 ? '' : 's'}`,
      ])),
    ]).flat()),
    theme: 'grid',
    styles: { fontSize: 9, cellPadding: 6, valign: 'top' },
    columnStyles: { 0: { cellWidth: width - 60 }, 1: { cellWidth: 60, halign: 'right' } },
    margin: { left: margin, right: margin },
  })

  /* ── Teacher copy ───────────────────────────────────────────────────────── */
  if (includeAnswers) {
    doc.addPage()
    let ay = 52
    doc.setFontSize(13)
    doc.setTextColor('#4F46E5')
    doc.text('Marking scheme (teacher copy)', margin, ay)
    ay += 18

    doc.setFontSize(10)
    doc.setTextColor('#111827')
    doc.text('Paper 1 — answers', margin, ay)
    ay += 10
    autoTable(doc, {
      startY: ay,
      head: [['#', 'Answer', '#', 'Answer']],
      body: chunkRows(
        paper.paper1.questions.map((question, index) => [
          `${index + 1}`,
          question.answerLetter ? `${question.answerLetter}. ${question.answer ?? ''}` : `${question.answer ?? ''}`,
        ]),
        2,
      ),
      theme: 'grid',
      styles: { fontSize: 8, cellPadding: 4 },
      headStyles: { fillColor: '#F1F5F9', textColor: '#334155' },
      columnStyles: { 0: { cellWidth: 30 }, 1: { cellWidth: (width - 60) / 2 - 30 }, 2: { cellWidth: 30 }, 3: { cellWidth: (width - 60) / 2 - 30 } },
      margin: { left: margin, right: margin },
    })
    ay = doc.lastAutoTable.finalY + 18

    doc.setFontSize(10)
    doc.setTextColor('#111827')
    doc.text('Paper 2 — answers', margin, ay)
    ay += 10
    autoTable(doc, {
      startY: ay,
      head: [['Q', 'Part', 'Answer', 'Marks']],
      body: paper.paper2.questions.flatMap((question) => question.parts.map((part) => ([
        `${question.number}`,
        `(${part.letter}) ${part.question.prompt || part.question.question || ''}`,
        `${part.question.answer ?? ''}`,
        `${part.marks}`,
      ]))),
      theme: 'grid',
      styles: { fontSize: 8, cellPadding: 5, valign: 'top' },
      headStyles: { fillColor: '#F1F5F9', textColor: '#334155' },
      columnStyles: {
        0: { cellWidth: 24 },
        1: { cellWidth: width * 0.34 },
        2: { cellWidth: width - 24 - 60 - width * 0.34 - 40 },
        3: { cellWidth: 40, halign: 'right' },
      },
      margin: { left: margin, right: margin },
    })
  }

  doc.setFontSize(8)
  doc.setTextColor('#94A3B8')
  doc.text('Generated with Beacon Educational Consult', margin, doc.internal.pageSize.getHeight() - 24)
  return doc
}

/** `[[1, a], [2, b], …]` read side by side — `[[1, a, 2, b], …]` — for the compact answer grid. */
function chunkRows(rows, perRow) {
  const out = []
  for (let i = 0; i < rows.length; i += perRow) {
    const pair = rows.slice(i, i + perRow).flat()
    while (pair.length < rows[0].length * perRow) pair.push('')
    out.push(pair)
  }
  return out
}

/** The composed mock → printable PDF download. */
export function downloadBecePaper(paper, options = {}) {
  buildBecePaper(paper, options).save(`BECE_Mock_${paper.subjectName || 'Mathematics'}.pdf`)
}
