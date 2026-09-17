import {
  Document,
  HeadingLevel,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
  Packer,
} from 'docx'
import type {
  Block,
  CalloutBlock,
  EquationBlock,
  MaterialDoc,
  TableBlock,
  TextBlock,
} from '../kernel/types'

// ── Block renderers ──────────────────────────────────────────

function renderTextBlock(block: TextBlock): Paragraph {
  if (block.style === 'heading') {
    return new Paragraph({ text: block.text, heading: HeadingLevel.HEADING_3 })
  }
  if (block.style === 'bullet') {
    return new Paragraph({ text: block.text, bullet: { level: 0 } })
  }
  return new Paragraph({ text: block.text })
}

function renderTableBlock(block: TableBlock): Table {
  const headerRow = new TableRow({
    children: block.headers.map(
      (h) =>
        new TableCell({
          children: [new Paragraph({ children: [new TextRun({ text: h, bold: true })] })],
        })
    ),
  })

  const dataRows = block.rows.map(
    (row) =>
      new TableRow({
        children: row.map(
          (cell) => new TableCell({ children: [new Paragraph({ text: cell })] })
        ),
      })
  )

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [headerRow, ...dataRows],
  })
}

function renderCalloutBlock(block: CalloutBlock): Paragraph {
  return new Paragraph({
    children: [
      new TextRun({ text: `${block.label}: `, bold: true }),
      new TextRun({ text: block.text }),
    ],
  })
}

function renderEquationBlock(block: EquationBlock): Paragraph {
  // Placeholder — swap in MathML or an image renderer here without
  // touching any subject module.
  return new Paragraph({ text: `[equation] ${block.latex}` })
}

function renderBlock(block: Block): Paragraph | Table {
  switch (block.type) {
    case 'text':    return renderTextBlock(block as TextBlock)
    case 'table':   return renderTableBlock(block as TableBlock)
    case 'callout': return renderCalloutBlock(block as CalloutBlock)
    case 'equation': return renderEquationBlock(block as EquationBlock)
  }
}

// ── Main render function ─────────────────────────────────────

export async function renderDocx(doc: MaterialDoc): Promise<Blob> {
  const children: (Paragraph | Table)[] = [
    new Paragraph({ text: doc.title, heading: HeadingLevel.HEADING_1 }),
  ]

  for (const section of doc.sections) {
    children.push(
      new Paragraph({ text: section.title, heading: HeadingLevel.HEADING_2 })
    )
    for (const block of section.blocks) {
      children.push(renderBlock(block))
    }
  }

  const document = new Document({ sections: [{ children }] })
  return Packer.toBlob(document)
}

// ── Convenience download helper ──────────────────────────────

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
