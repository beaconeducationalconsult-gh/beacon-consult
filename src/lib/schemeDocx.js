import { Document, Packer, Paragraph } from 'docx'
import { H2, para, table, titleBlock, brandedFooter, labelValue, BRAND } from './docxShared'
import { gradeLabel } from './grades'

/**
 * Scheme of Learning → .docx  (client-side, no server)
 * Mirrors the structure of the printed scheme books.
 */
export async function downloadSchemeDocx(scheme, { school, teacher } = {}) {
  const children = [
    ...titleBlock(
      `Scheme of Learning — ${scheme.subjectName || scheme.subjectId}`,
      `${gradeLabel(scheme.grade)} · Term ${scheme.term}`
    ),
    ...(school ? [labelValue('School', school)] : []),
    ...(teacher ? [labelValue('Teacher', teacher)] : []),
    labelValue('Prepared', new Date().toLocaleDateString('en-GB')),
    para(''),

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
      [5, 22, 26, 32, 15]
    ),
  ]

  if (scheme.notes) {
    children.push(new Paragraph({ text: 'Notes', heading: H2 }), para(scheme.notes))
  }

  children.push(brandedFooter())

  const doc = new Document({
    creator: BRAND.name,
    title: `Scheme of Learning — ${scheme.subjectName || scheme.subjectId} ${scheme.grade}`,
    sections: [{ properties: { page: { size: { orientation: 'landscape' } } }, children }],
  })

  return Packer.toBlob(doc)
}
