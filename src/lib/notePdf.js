import { jsPDF } from 'jspdf'
import { htmlToBlocks } from './htmlBlocks'
import { gradeLabel } from './grades'

/**
 * Study note → PDF (client-side, A4 portrait).
 *
 * One text flow rather than a table: a note is prose. Headings are drawn in the
 * brand colour and slightly larger; list items get a bullet or a literal number.
 * The reader is `htmlToBlocks`, shared with the Word export, so the two files
 * carry the same content in the same order.
 */
export function buildNotePdf(note, { school, teacher } = {}) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const margin = 48
  const width = doc.internal.pageSize.getWidth() - margin * 2
  const height = doc.internal.pageSize.getHeight()
  let y = 56

  const room = (needed) => {
    // Keep the footer clear, and start a new page when the block would not fit.
    if (y + needed > height - 56) {
      doc.addPage()
      y = 56
    }
  }

  doc.setFontSize(9)
  doc.setTextColor('#64748B')
  doc.text('BEACON EDUCATIONAL CONSULT · STUDY NOTE', margin, y)
  y += 22

  doc.setFontSize(18)
  doc.setTextColor('#111827')
  for (const line of doc.splitTextToSize(note.title || 'Untitled note', width)) {
    room(24)
    doc.text(line, margin, y)
    y += 22
  }

  doc.setFontSize(10)
  doc.setTextColor('#4F46E5')
  const meta = [
    note.subjectName || note.subjectId,
    gradeLabel(note.grade),
    note.authorName,
    school ? `School: ${school}` : null,
    teacher ? `Teacher: ${teacher}` : null,
  ].filter(Boolean).join(' · ')
  for (const line of doc.splitTextToSize(meta, width)) {
    room(14)
    doc.text(line, margin, y)
    y += 14
  }
  y += 6

  if (note.summary) {
    doc.setFontSize(11)
    doc.setTextColor('#334155')
    const lines = doc.splitTextToSize(note.summary, width)
    room(lines.length * 14 + 10)
    doc.text(lines, margin, y)
    y += lines.length * 14 + 10
  }

  doc.setDrawColor('#E2E8F0')
  doc.line(margin, y, margin + width, y)
  y += 18

  for (const block of htmlToBlocks(note.content)) {
    if (block.type === 'heading') {
      const size = block.level === 1 ? 15 : block.level === 2 ? 13 : 12
      doc.setFontSize(size)
      doc.setTextColor('#4F46E5')
      const lines = doc.splitTextToSize(block.text, width)
      room(lines.length * (size + 4) + 6)
      doc.text(lines, margin, y)
      y += lines.length * (size + 4) + 6
      continue
    }
    const size = block.type === 'paragraph' ? 11 : 10.5
    doc.setFontSize(size)
    doc.setTextColor('#334155')
    const prefix = block.type === 'bullet' ? '•  ' : block.type === 'numbered' ? '1.  ' : ''
    const indent = prefix ? 14 : 0
    const lines = doc.splitTextToSize(block.text, width - indent)
    room(lines.length * (size + 4) + 6)
    if (prefix) doc.text(prefix.trim(), margin, y)
    doc.text(lines, margin + indent, y)
    y += lines.length * (size + 4) + 6
  }

  doc.setFontSize(8)
  doc.setTextColor('#94A3B8')
  doc.text('Generated with Beacon Educational Consult', margin, height - 28)

  return doc
}

/** Study note → PDF download. */
export function downloadNotePdf(note, meta = {}) {
  buildNotePdf(note, meta).save(`Note_${(note.subjectId || 'note')}_${note.grade || ''}.pdf`)
}
