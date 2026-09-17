import { AlignmentType, Paragraph, Table, TableCell, TableRow, TextRun, WidthType, HeadingLevel, BorderStyle } from 'docx'

/*
 * Shared Word-generation helpers used by every *Docx exporter.
 * Branding is applied here so each exporter only describes content.
 * See docs/shared-code.md and docs/book-structure.md.
 */

export const BRAND = {
  name: 'Beacon Educational Consult',
  primary: '4F46E5',
  accent: 'F59E0B',
  muted: '64748B',
}

export const H1 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_1 })
export const H2 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_2 })
export const H3 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_3 })

export function para(text, options = {}) {
  return new Paragraph({
    alignment: options.alignment,
    spacing: { after: options.after ?? 120 },
    children: [
      new TextRun({
        text: String(text ?? ''),
        bold: options.bold,
        italics: options.italics,
        size: options.size ?? 22, // half-points: 22 = 11pt
        color: options.color,
      }),
    ],
  })
}

export function labelValue(label, value) {
  return new Paragraph({
    spacing: { after: 60 },
    children: [
      new TextRun({ text: `${label}: `, bold: true, size: 22 }),
      new TextRun({ text: String(value ?? '—'), size: 22 }),
    ],
  })
}

export function bullet(text, level = 0) {
  return new Paragraph({ text: String(text ?? ''), bullet: { level }, spacing: { after: 60 } })
}

const CELL_BORDER = { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' }

export function cell(text, { bold = false, width, shade } = {}) {
  return new TableCell({
    borders: { top: CELL_BORDER, bottom: CELL_BORDER, left: CELL_BORDER, right: CELL_BORDER },
    shading: shade ? { fill: shade } : undefined,
    width: width ? { size: width, type: WidthType.PERCENTAGE } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [
      new Paragraph({
        children: [new TextRun({ text: String(text ?? ''), bold, size: 20 })],
      }),
    ],
  })
}

/** headers: string[]; rows: (string|number)[][]; widths: percentage per column. */
export function table(headers, rows, widths) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, { bold: true, width: widths?.[i], shade: 'F1F5F9' })),
      }),
      ...rows.map((row) => new TableRow({ children: row.map((c, i) => cell(c, { width: widths?.[i] })) })),
    ],
  })
}

export function titleBlock(title, subtitle) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [new TextRun({ text: title, bold: true, size: 34, color: BRAND.primary })],
    }),
    subtitle
      ? new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 240 },
          children: [new TextRun({ text: subtitle, size: 22, color: BRAND.muted })],
        })
      : para(''),
  ]
}

/** The footer every exported document carries. */
export function brandedFooter() {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 240 },
    children: [
      new TextRun({ text: `Generated with ${BRAND.name}`, size: 18, color: BRAND.muted }),
    ],
  })
}
