import { Document, Packer, Paragraph, TextRun } from 'docx'
import { htmlToBlocks } from './htmlBlocks'
import {
  H3,
  bullet,
  metaLine,
  para,
  documentStyles,
  brandedFooter,
  titleBlock,
  referenceTable,
  fill,
} from './docxShared'
import { gradeLabel } from './grades'

const HEADINGS = [H3, 'Heading4', 'Heading5', 'Heading6']

/**
 * Study note → .docx (client-side).
 *
 * A note is HTML, so `htmlToBlocks` turns it into headings, paragraphs and
 * lists; the same reader feeds the PDF export, so the two files agree. Numbers
 * use a literal "1." prefix rather than Word's automatic list numbering, which
 * would restart in every document and cannot be reasoned about outside Word.
 */
export async function downloadNoteDocx(note, { school, teacher } = {}) {
  const blocks = htmlToBlocks(note.content)
  const children = [
    ...titleBlock('STUDY NOTE', [note.subjectName || note.subjectId, gradeLabel(note.grade)]
      .filter(Boolean).join('  ·  ').toUpperCase()),
    metaLine([['Title', note.title || '']]),
    metaLine([
      ['School', fill(school)],
      ['Teacher', fill(teacher)],
    ]),
    referenceTable([
      ['Written by', note.authorName || ''],
      ['Date', new Date(note.createdAt?.seconds ? note.createdAt.seconds * 1000 : Date.now())
        .toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })],
      ...(note.summary ? [['Summary', note.summary]] : []),
    ]),
    ...blocks.map((block) => {
      if (block.type === 'heading') {
        return new Paragraph({ text: block.text, heading: HEADINGS[Math.min(block.level, 4) - 1] || H3 })
      }
      if (block.type === 'bullet') return bullet(block.text)
      if (block.type === 'numbered') return para(`1.  ${block.text}`)
      return new Paragraph({ children: [new TextRun({ text: block.text })] })
    }),
  ]

  const doc = new Document({
    styles: documentStyles(),
    sections: [{ footers: { default: brandedFooter() }, children }],
  })
  return Packer.toBlob(doc)
}
