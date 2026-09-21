import { Document, Packer, Paragraph } from 'docx'
import {
  H2,
  CONTENT_WIDTH,
  para,
  table,
  fill,
  metaLine,
  titleBlock,
  documentStyles,
  brandedFooter,
} from './docxShared'
import { gradeLabel } from './grades'

/**
 * Scheme of Learning → .docx  (client-side, no server)
 *
 * Mirrors the structure of the printed scheme books: a ruled title block, the
 * school's own details, then one wide landscape table of the term's weeks.
 */
export async function downloadSchemeDocx(scheme, { school, teacher } = {}) {
  const subject = scheme.subjectName || scheme.subjectId || ''

  const children = [
    ...titleBlock(
      `SCHEME OF LEARNING — ${subject.toUpperCase()}`,
      [gradeLabel(scheme.grade).toUpperCase(), `TERM ${scheme.term}`].filter(Boolean).join('  ·  ')
    ),
    metaLine([
      ['School', fill(school)],
      ['Teacher', fill(teacher)],
    ]),
    metaLine([
      ['Prepared', new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })],
      ['Term', scheme.term || '—'],
    ]),

    new Paragraph({ text: 'Weekly Plan', heading: H2 }),
    table(
      ['Wk', 'Strand / Sub-strand', 'Content Standard', 'Indicators', 'Resources'],
      (scheme.rows || []).map((row) => [
        row.week ?? '',
        [row.strandName, row.subStrandName].filter(Boolean).join(' — '),
        row.contentStandard || row.contentStandardDescription || '',
        row.indicators || (row.indicatorCodes || []).join(', ') || '',
        row.resources || '',
      ]),
      [5, 22, 26, 32, 15],
      { contentWidth: CONTENT_WIDTH.landscape }
    ),
  ]

  if (scheme.notes) {
    children.push(new Paragraph({ text: 'Notes', heading: H2 }), para(scheme.notes))
  }

  const doc = new Document({
    creator: 'Beacon Educational Consult',
    title: `Scheme of Learning — ${subject} ${scheme.grade}`,
    styles: documentStyles(),
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838, orientation: 'landscape' },
            margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 },
          },
        },
        footers: { default: brandedFooter({ tabPosition: CONTENT_WIDTH.landscape }) },
        children,
      },
    ],
  })

  return Packer.toBlob(doc)
}
