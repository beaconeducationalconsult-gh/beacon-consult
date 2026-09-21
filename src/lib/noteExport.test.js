import { describe, expect, it } from 'vitest'
import JSZip from 'jszip'
import { htmlToBlocks, decodeEntities, blocksToText } from './htmlBlocks'
import { downloadNoteDocx } from './noteDocx'
import { buildNotePdf } from './notePdf'

/*
 * Study notes are stored as HTML and exported to Word and PDF (P3-5). Both
 * exporters read the note through `htmlToBlocks`, so these tests start there:
 * if the reader loses a bullet or swallows a paragraph, both files are wrong in
 * the same way, and it is the reader that has to be fixed.
 */

const NOTE = {
  id: 'note1',
  title: 'Place value in Basic 4',
  subjectId: 'mathematics',
  subjectName: 'Mathematics',
  grade: 'B4',
  authorName: 'Mr K. Mensah',
  summary: 'A one-page revision sheet for the first week of term.',
  createdAt: { seconds: 1750000000 },
  content: `
    <h1>Place value</h1>
    <p>Every digit has a <strong>value</strong> that depends on its position.</p>
    <ul>
      <li>4 520 — the 4 is worth 4 000</li>
      <li>The 5 is worth 500</li>
    </ul>
    <h2>Worked example</h2>
    <p>Write 7 306 in words.<br>Seven thousand three hundred and six.</p>
    <ol>
      <li>Say the thousands first</li>
      <li>Then the hundreds</li>
    </ol>
    <p>3 &times; 100 = 300 &mdash; not 30.</p>
  `,
}

describe('the HTML reader behind the note exports', () => {
  it('keeps headings, paragraphs and both list kinds, in order', () => {
    const blocks = htmlToBlocks(NOTE.content)
    expect(blocks.map((b) => b.type)).toEqual([
      'heading', 'paragraph', 'bullet', 'bullet',
      'heading', 'paragraph', 'numbered', 'numbered', 'paragraph',
    ])
    expect(blocks[0]).toMatchObject({ type: 'heading', level: 1, text: 'Place value' })
    expect(blocks[4]).toMatchObject({ type: 'heading', level: 2, text: 'Worked example' })
  })

  it('drops inline markup but keeps its text', () => {
    const [paragraph] = htmlToBlocks('<p>Every digit has a <strong>value</strong>.</p>')
    expect(paragraph.text).toBe('Every digit has a value.')
  })

  it('turns a <br> inside a paragraph into a space, not a new block', () => {
    const blocks = htmlToBlocks('<p>first<br>second</p>')
    expect(blocks).toHaveLength(1)
    expect(blocks[0].text).toBe('first second')
  })

  it('decodes the entities a rich-text editor writes', () => {
    expect(decodeEntities('3 &times; 100 &mdash; 30&nbsp;%')).toBe('3 × 100 — 30 %')
    expect(decodeEntities('&#39;quoted&#39; and &#x2014; dash')).toBe("'quoted' and — dash")
    // An entity it does not know is left alone rather than mangled.
    expect(decodeEntities('&weird;')).toBe('&weird;')
  })

  it('survives empty, plain and malformed content', () => {
    expect(htmlToBlocks('')).toEqual([])
    expect(htmlToBlocks(null)).toEqual([])
    expect(htmlToBlocks('just text')).toEqual([{ type: 'paragraph', text: 'just text' }])
    // Unclosed tags: everything written is still in the output.
    expect(blocksToText(htmlToBlocks('<p>one<p>two'))).toBe('one\ntwo')
  })

  it('collapses the whitespace Tiptap leaves between blocks', () => {
    const blocks = htmlToBlocks('<p>\n  spaced   out\n</p>')
    expect(blocks[0].text).toBe('spaced out')
  })
})

describe('the note .docx', () => {
  const unzip = async (blob) => {
    const zip = await JSZip.loadAsync(Buffer.from(await blob.arrayBuffer()))
    const parts = {}
    for (const name of Object.keys(zip.files)) {
      if (name.endsWith('.xml')) parts[name] = await zip.files[name].async('string')
    }
    return parts
  }

  it('writes the note title, body and list items into the document', async () => {
    const parts = await unzip(await downloadNoteDocx(NOTE, { school: 'Beacon Basic School', teacher: 'Mr K. Mensah' }))
    const doc = parts['word/document.xml']
    for (const text of ['STUDY NOTE', 'Place value', 'Every digit has a', '4 000', 'Worked example', '7 306', '3 × 100 = 300 — not 30.']) {
      expect(doc, `the Word note lost "${text}"`).toBeTruthy()
    }
    expect(doc).toContain('Place value in Basic 4')
    expect(doc).toContain('Beacon Basic School')
  })

  it('uses heading styles that exist, and defines them', async () => {
    const parts = await unzip(await downloadNoteDocx(NOTE))
    const declared = new Set([...parts['word/styles.xml'].matchAll(/w:styleId="([^"]+)"/g)].map((m) => m[1]))
    const referenced = [...parts['word/document.xml'].matchAll(/<w:pStyle w:val="([^"]*)"/g)].map((m) => m[1])
    expect(referenced.filter((s) => !declared.has(s))).toEqual([])
    expect([...declared].some((s) => s.startsWith('Heading'))).toBe(true)
  })
})

describe('the note .pdf', () => {
  it('is a real PDF with the note on it', () => {
    const doc = buildNotePdf(NOTE, { school: 'Beacon Basic School' })
    const bytes = Buffer.from(doc.output('arraybuffer'))
    expect(bytes.subarray(0, 5).toString('latin1')).toBe('%PDF-')
    expect(bytes.subarray(-6).toString('latin1').trimEnd()).toMatch(/%%EOF$/)
    expect(doc.getNumberOfPages()).toBeGreaterThanOrEqual(1)
    expect(Math.round(doc.internal.pageSize.getWidth())).toBe(595) // A4 portrait
  })

  it('flows a long note onto more pages instead of off the sheet', () => {
    const long = { ...NOTE, content: `<p>${'Fill the page and then some. '.repeat(600)}</p>` }
    expect(buildNotePdf(long).getNumberOfPages()).toBeGreaterThan(1)
  })

  it('renders a note with no content at all', () => {
    const bare = { ...NOTE, content: '', summary: '' }
    expect(buildNotePdf(bare).getNumberOfPages()).toBe(1)
  })
})
