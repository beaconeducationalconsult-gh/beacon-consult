import {
  AlignmentType,
  BorderStyle,
  Footer,
  HeadingLevel,
  PageNumber,
  Paragraph,
  Table,
  TableCell,
  TableLayoutType,
  TableRow,
  TabStopType,
  TextRun,
  VerticalAlign,
  WidthType,
} from 'docx'

/*
 * Shared Word-generation helpers used by every *Docx exporter.
 *
 * Two rules keep an exported document looking like the printed Beacon books
 * (`scripts/generate_schemes.py` is the reference implementation):
 *
 *   1. Nothing depends on Word's built-in styles or on the reader's Normal
 *      template. Fonts, sizes, colours and heading looks are declared here, so
 *      the document opens the same on every machine.
 *   2. Callers describe content only. Branding, spacing and page furniture
 *      live in this file.
 *
 * See docs/shared-code.md.
 */

/** OOXML sizes are half-points: 22 = 11pt. */
const PT = (points) => points * 2

/** The printed books are Calibri; a Word export has to match them. */
export const FONT = 'Calibri'

/** Print colours — the same ones `scripts/generate_schemes.py` uses. */
export const BRAND = {
  name: 'Beacon Educational Consult',
  navy: '002060',
  gray: '404040',
  muted: '6B7280',
  rule: '9AA5B1',
  band: 'EDF0F5',
}

export const SIZE = {
  title: PT(18),
  subtitle: PT(11),
  heading: PT(12),
  subheading: PT(11),
  body: PT(11),
  meta: PT(10),
  table: PT(9),
  footer: PT(8),
}

/**
 * Real heading levels — pass one to `new Paragraph({ text, heading: H2 })`.
 *
 * These used to be paragraph factories, which meant every caller passed a
 * *function* where OOXML expects a level name: the document asked Word for a
 * style called "(text) => new Paragraph(…)", Word could not find it, and every
 * section heading silently rendered as ordinary body text — no bold, no size
 * jump, no outline entry. A function is not a heading level.
 */
export const H1 = HeadingLevel.HEADING_1
export const H2 = HeadingLevel.HEADING_2
export const H3 = HeadingLevel.HEADING_3

/**
 * How much of an A4 page is left for tables, in twips.
 * A4 is 11906 x 16838; both exporters set 1080 (0.75in) margins, so the text
 * column is the page minus 2160. These must stay in step with the `margin` in
 * each section's `page` properties.
 */
export const CONTENT_WIDTH = { portrait: 9746, landscape: 14678 }

/**
 * Document-wide styles. Pass to `new Document({ styles: documentStyles() })`.
 * Declaring the defaults is what fixes the font: without them the body font is
 * whatever the reader's Normal template happens to be.
 */
export function documentStyles() {
  return {
    default: {
      document: {
        run: { font: FONT, size: SIZE.body, color: BRAND.gray },
        paragraph: { spacing: { after: 120, line: 264 } },
      },
      heading1: {
        run: { font: FONT, size: SIZE.title, bold: true, color: BRAND.navy },
        paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, keepLines: true },
      },
      heading2: {
        run: { font: FONT, size: SIZE.heading, bold: true, color: BRAND.navy },
        paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, keepLines: true },
      },
      heading3: {
        run: { font: FONT, size: SIZE.subheading, bold: true, color: BRAND.gray },
        paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, keepLines: true },
      },
      listParagraph: {
        run: { font: FONT, size: SIZE.body, color: BRAND.gray },
        paragraph: { spacing: { after: 100 } },
      },
    },
  }
}

export const para = (text, options = {}) =>
  new Paragraph({
    alignment: options.alignment,
    indent: options.indent,
    spacing: { after: options.after ?? 120 },
    children: [
      new TextRun({
        text: String(text ?? ''),
        bold: options.bold,
        italics: options.italics,
        size: options.size ?? SIZE.body,
        color: options.color,
      }),
    ],
  })

export const labelValue = (label, value) =>
  new Paragraph({
    spacing: { after: 60 },
    children: [
      new TextRun({ text: `${label}: `, bold: true, size: SIZE.meta, font: FONT }),
      new TextRun({ text: String(value ?? '—'), size: SIZE.meta, font: FONT }),
    ],
  })

export const bullet = (text, level = 0) =>
  new Paragraph({
    text: String(text ?? ''),
    bullet: { level },
    spacing: { after: 100 },
  })

/**
 * A numbered step. The number is part of the text rather than an auto-numbered
 * list so it cannot renumber itself if a teacher edits the document later, and
 * the hanging indent keeps wrapped lines under the words, not under the number.
 */
export const step = (index, text) =>
  new Paragraph({
    indent: { left: 360, hanging: 360 },
    spacing: { after: 100 },
    children: [
      new TextRun({ text: `${index}.  `, bold: true, size: SIZE.body, font: FONT }),
      new TextRun({ text: String(text ?? ''), size: SIZE.body, font: FONT }),
    ],
  })

/** A horizontal rule, drawn as a paragraph border (the printed books do this). */
export const rule = (color = BRAND.rule, size = 6) =>
  new Paragraph({
    spacing: { before: 0, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size, color, space: 1 } },
    children: [new TextRun({ text: '', size: 2 })],
  })

const CELL_BORDER = { style: BorderStyle.SINGLE, size: 2, color: BRAND.rule }
const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }

export function cell(text, { bold = false, width, shade, span, size = SIZE.table, align, borders, valign } = {}) {
  return new TableCell({
    borders: borders ?? { top: CELL_BORDER, bottom: CELL_BORDER, left: CELL_BORDER, right: CELL_BORDER },
    shading: shade ? { fill: shade } : undefined,
    columnSpan: span,
    verticalAlign: valign ?? VerticalAlign.CENTER,
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [
      new Paragraph({
        alignment: align,
        spacing: { after: 0 },
        children: [new TextRun({ text: String(text ?? ''), bold, size, color: BRAND.gray, font: FONT })],
      }),
    ],
  })
}

/**
 * headers: string[]; rows: (string|number)[][]; widths: percentage per column.
 *
 * Widths are converted to absolute twips because Word honours a percentage
 * table by re-fitting the columns to the content, which is how a 5-column
 * scheme table ends up with one long sentence squeezed into a 2cm column.
 */
export function table(headers, rows, widths, { contentWidth = CONTENT_WIDTH.portrait } = {}) {
  const pct = widths ?? headers.map(() => 100 / headers.length)
  const dxa = pct.map((p) => Math.round((p / 100) * contentWidth))
  return new Table({
    width: { size: contentWidth, type: WidthType.DXA },
    columnWidths: dxa,
    layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, { bold: true, width: dxa[i], shade: BRAND.band })),
      }),
      ...rows.map((row) => new TableRow({ children: row.map((c, i) => cell(c, { width: dxa[i] })) })),
    ],
  })
}

/**
 * Label/value list as a borderless two-column table. Long reference text (a
 * content standard runs to two lines) needs a real label column; as inline
 * "Label: value" paragraphs it reads as one wall of prose.
 */
export function referenceTable(rows, { contentWidth = CONTENT_WIDTH.portrait, labelWidth = 26 } = {}) {
  const label = Math.round((labelWidth / 100) * contentWidth)
  const value = contentWidth - label
  const border = { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER }
  return new Table({
    width: { size: contentWidth, type: WidthType.DXA },
    columnWidths: [label, value],
    layout: TableLayoutType.FIXED,
    // Borderless at the table level too, not only per cell: the library's
    // default table borders are single/auto, and leaving them on makes the
    // reference block look like a spreadsheet rather than a letterhead.
    borders: { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER, insideHorizontal: NO_BORDER, insideVertical: NO_BORDER },
    rows: rows.map(
      ([k, v]) =>
        new TableRow({
          children: [
            cell(k, { bold: true, width: label, size: SIZE.table, borders: border, valign: VerticalAlign.TOP }),
            cell(v, { width: value, size: SIZE.table, borders: border, valign: VerticalAlign.TOP }),
          ],
        })
    ),
  })
}

/** Centred document title, subtitle and the rule under them. */
export function titleBlock(title, subtitle) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: [new TextRun({ text: title, bold: true, size: SIZE.title, color: BRAND.navy, font: FONT })],
    }),
    ...(subtitle
      ? [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { after: 40 },
            children: [new TextRun({ text: subtitle, size: SIZE.subtitle, color: BRAND.gray, font: FONT })],
          }),
        ]
      : []),
    rule(BRAND.navy, 8),
  ]
}

/**
 * The printed books leave a ruled blank where a field is unknown, so a teacher
 * can fill it in by hand. A document generated for a school comes out
 * pre-filled; a blank one is still usable.
 */
export const fill = (value, width = 28) => (value ? String(value) : '_'.repeat(width))

/** One line of two or three `Label: value` fields, as the books lay them out. */
export const metaLine = (pairs) =>
  new Paragraph({
    spacing: { after: 60 },
    children: pairs.flatMap(([label, value], i) => [
      new TextRun({ text: `${i ? '        ' : ''}${label}: `, bold: true, size: SIZE.meta, font: FONT }),
      new TextRun({ text: String(value ?? ''), size: SIZE.meta, font: FONT }),
    ]),
  })

/** Signature and date lines — the books use underscores, not a table. */
export const signatureLines = (rows) =>
  rows.map(
    ([label, name]) =>
      new Paragraph({
        spacing: { after: 200 },
        children: [
          new TextRun({ text: `${label}: `, bold: true, size: SIZE.meta, font: FONT }),
          new TextRun({ text: name || '_'.repeat(32), size: SIZE.meta, font: FONT }),
          new TextRun({ text: '      Signature: ', bold: true, size: SIZE.meta, font: FONT }),
          new TextRun({ text: '_'.repeat(24), size: SIZE.meta, font: FONT }),
          new TextRun({ text: '      Date: ', bold: true, size: SIZE.meta, font: FONT }),
          new TextRun({ text: '_'.repeat(14), size: SIZE.meta, font: FONT }),
        ],
      })
  )

/**
 * The running footer. A real footer repeats on every page; a paragraph at the
 * end of the body only ever printed on the last one, halfway up.
 */
export function brandedFooter({ tabPosition = CONTENT_WIDTH.portrait } = {}) {
  const run = (text, extra = {}) => new TextRun({ text, size: SIZE.footer, color: BRAND.muted, font: FONT, ...extra })
  const field = (children) => new TextRun({ children, size: SIZE.footer, color: BRAND.muted, font: FONT })
  return new Footer({
    children: [
      new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: BRAND.rule, space: 4 } },
        tabStops: [{ type: TabStopType.RIGHT, position: tabPosition }],
        children: [
          run(`${BRAND.name}  ·  ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}`),
          run('\t'),
          run('Page '),
          field([PageNumber.CURRENT]),
          run(' of '),
          field([PageNumber.TOTAL_PAGES]),
        ],
      }),
    ],
  })
}
