import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { gradeLabel } from './grades'

/*
 * The document builders are exported separately from the `download…` wrappers
 * so the output can be tested without a DOM: `downloadSchemePdf` calls
 * `doc.save()`, which needs a browser, while `buildSchemePdf` returns the jsPDF
 * instance. `src/lib/pdfExport.test.js` holds the builders to their invariants
 * (orientation, page count, the text a teacher would look for).
 */

/** Scheme of Learning → jsPDF document. Landscape A4, mirrors the Word export. */
export function buildSchemePdf(scheme, { school, teacher } = {}) {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' })
  const title = `Scheme of Learning — ${scheme.subjectName || scheme.subjectId}`
  const subtitle = `${gradeLabel(scheme.grade)} · Term ${scheme.term}`

  doc.setFontSize(16)
  doc.setTextColor('#4F46E5')
  doc.text(title, 40, 48)
  doc.setFontSize(11)
  doc.setTextColor('#64748B')
  doc.text(subtitle, 40, 66)

  let cursor = 88
  doc.setFontSize(10)
  doc.setTextColor('#334155')
  if (school) {
    doc.text(`School: ${school}`, 40, cursor)
    cursor += 14
  }
  if (teacher) {
    doc.text(`Teacher: ${teacher}`, 40, cursor)
    cursor += 14
  }

  autoTable(doc, {
    startY: cursor + 8,
    head: [['Wk', 'Strand / Sub-strand', 'Content Standard', 'Indicators', 'Resources']],
    body: (scheme.rows || []).map((row) => [
      row.week ?? '',
      [row.strandName, row.subStrandName].filter(Boolean).join(' — '),
      row.contentStandard || row.contentStandardDescription || '',
      row.indicators || (row.indicatorCodes || []).join(', ') || '',
      row.resources || '',
    ]),
    styles: { fontSize: 8, cellPadding: 5, overflow: 'linebreak' },
    headStyles: { fillColor: '#4F46E5', textColor: '#FFFFFF' },
    alternateRowStyles: { fillColor: '#F8FAFC' },
    columnStyles: {
      0: { cellWidth: 30 },
      1: { cellWidth: 150 },
      2: { cellWidth: 190 },
      3: { cellWidth: 230 },
      4: { cellWidth: 110 },
    },
  })

  if (scheme.notes) {
    const y = doc.lastAutoTable.finalY + 24
    doc.setFontSize(11)
    doc.setTextColor('#4F46E5')
    doc.text('Notes', 40, y)
    doc.setFontSize(9)
    doc.setTextColor('#334155')
    doc.text(doc.splitTextToSize(scheme.notes, 740), 40, y + 16)
  }

  doc.setFontSize(8)
  doc.setTextColor('#94A3B8')
  doc.text('Generated with Beacon Educational Consult', 40, doc.internal.pageSize.getHeight() - 24)

  return doc
}

/** Scheme of Learning → PDF download (client-side). */
export function downloadSchemePdf(scheme, meta = {}) {
  buildSchemePdf(scheme, meta).save(`Scheme_${scheme.subjectId}_${scheme.grade}_T${scheme.term}.pdf`)
}
