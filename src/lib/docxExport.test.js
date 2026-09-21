import { describe, expect, it } from 'vitest'
import JSZip from 'jszip'
import { downloadLessonPlanDocx } from './lessonPlanDocx'
import { downloadSchemeDocx } from './schemeDocx'

/*
 * The Word exports are the product a teacher prints and hands in, and they are
 * the one part of the app no test could see. They shipped broken: every section
 * heading was written as a paragraph whose *style name was the source text of a
 * function*, because `heading: H2` was handed a paragraph factory instead of a
 * heading level. Word could not find that style, silently fell back to Normal,
 * and the document came out as one undifferentiated block of text.
 *
 * These tests unzip the generated .docx and check the parts a reader's Word
 * actually obeys, so that class of bug cannot come back unnoticed.
 */

/** Blob → { 'word/document.xml': '<w:document…' } for the parts we inspect. */
async function unzip(blob) {
  const zip = await JSZip.loadAsync(Buffer.from(await blob.arrayBuffer()))
  const parts = {}
  for (const name of Object.keys(zip.files)) {
    if (name.endsWith('.xml') || name.endsWith('.rels')) parts[name] = await zip.files[name].async('string')
  }
  return parts
}

const PLAN = {
  subjectId: 'mathematics',
  subjectName: 'Mathematics',
  grade: 'B4',
  term: 1,
  week: 2,
  durationMinutes: 60,
  indicatorCodes: ['B4.1.1.1.3'],
  indicatorCode: 'B4.1.1.1.3',
  strandName: 'NUMBER',
  subStrandName: 'Sub-strand B4.1.1',
  contentStandard: 'Demonstrate an understanding of quantities and place value for multi-digit whole numerals up to 100,000.',
  indicatorDescription: 'Identify numbers in different positions around a given number',
  performanceIndicator: 'By the end of the lesson, learners will be able to identify numbers in different positions',
  keywords: ['place value', 'numeration'],
  resources: ['NaCCA approved textbook', 'TLMs'],
  competencies: ['Critical Thinking and Problem Solving'],
  rpk: 'Learners used number charts and place-value cards in Basic 3.',
  starter: ['Greet learners; mental maths drill.'],
  main: ['ACTIVITY 1: Teacher models with manipulatives.', 'ACTIVITY 2: Learners work in pairs.'],
  plenary: ['Quick-fire oral quiz on today\u2019s skill.'],
  assessment: 'Class exercises; oral questions.',
  differentiation: 'Support: provide place-value cards.',
  objectives: ['read and write multi-digit numerals in words and figures'],
}

const SCHEME = {
  subjectId: 'mathematics',
  subjectName: 'Mathematics',
  grade: 'B4',
  term: 1,
  rows: [
    {
      week: 1,
      strandName: 'NUMBER',
      subStrandName: 'Sub-strand B4.1.1',
      contentStandard: 'Demonstrate an understanding of quantities and place value.',
      indicators: 'Model number quantities up to 100,000',
      resources: 'NaCCA approved textbook',
    },
  ],
}

const buildPlanWith = (over) =>
  downloadLessonPlanDocx({ ...PLAN, ...over }, { school: 'Beacon Basic School', teacher: 'Mr K. Mensah' })

const build = {
  lessonPlan: () => downloadLessonPlanDocx(PLAN, { school: 'Beacon Basic School', teacher: 'Mr K. Mensah' }),
  scheme: () => downloadSchemeDocx(SCHEME, { school: 'Beacon Basic School', teacher: 'Mr K. Mensah' }),
}

const DOCS = [
  ['lesson plan', build.lessonPlan],
  ['scheme', build.scheme],
]

describe.each(DOCS)('%s .docx', (_name, buildDoc) => {
  it('never references a style it does not define', async () => {
    const parts = await unzip(await buildDoc())
    const declared = new Set([...parts['word/styles.xml'].matchAll(/w:styleId="([^"]+)"/g)].map((m) => m[1]))
    const referenced = [...parts['word/document.xml'].matchAll(/<w:pStyle w:val="([^"]*)"/g)].map((m) => m[1])
    // A style name Word cannot resolve is silently dropped and the paragraph
    // renders as body text — which is how the headings disappeared.
    expect(referenced.filter((s) => !declared.has(s))).toEqual([])
    expect([...declared].some((s) => s.startsWith('Heading'))).toBe(true)
  })

  it('carries no source code in place of a style', async () => {
    const parts = await unzip(await buildDoc())
    // The original bug put `(text) => new Paragraph({ text, heading: … })` into
    // the document as a style name.
    expect(parts['word/document.xml']).not.toContain('=>')
    expect(parts['word/document.xml']).not.toMatch(/w:val="[^"]*Paragraph\(/)
  })

  it('declares its own font and size instead of inheriting Word\u2019s default', async () => {
    const parts = await unzip(await buildDoc())
    const defaults = /<w:docDefaults>.*?<\/w:docDefaults>/s.exec(parts['word/styles.xml'])[0]
    // Without this the document renders in whatever the reader's Normal
    // template happens to be, so it looks different on every machine.
    expect(defaults).toMatch(/<w:rFonts [^>]*w:ascii="Calibri"/)
    expect(defaults).toMatch(/<w:sz w:val="22"/)
  })

  it('is A4 with a text column its tables can actually fill', async () => {
    const parts = await unzip(await buildDoc())
    // A4 is 11906 x 16838 twips, in either orientation.
    const [, w, h] = /<w:pgSz w:w="(\d+)" w:h="(\d+)"/.exec(parts['word/document.xml']).map(Number)
    expect([w, h].sort((a, b) => a - b)).toEqual([11906, 16838])
    // Fixed layout is what makes the declared column widths stick; without it
    // Word refits every column to its content.
    expect(parts['word/document.xml']).toMatch(/<w:tblLayout w:type="fixed"/)
  })

  it('puts the running footer on the page, not in the body', async () => {
    const parts = await unzip(await buildDoc())
    expect(parts['word/document.xml']).toMatch(/<w:footerReference /)
    const footer = Object.keys(parts).find((p) => p.startsWith('word/footer'))
    expect(footer, 'a footer part is written').toBeTruthy()
    // A real footer repeats on every page; the old one was a paragraph at the
    // end of the body, printed once, halfway up the last page.
    expect(parts[footer]).toContain('Page')
  })
})

describe('lesson plan layout', () => {
  it('gives every section a real heading', async () => {
    const parts = await unzip(await build.lessonPlan())
    const doc = parts['word/document.xml']
    const headings = [...doc.matchAll(/<w:pStyle w:val="Heading2"\/><\/w:pPr>(?:(?!<\/w:p>).)*?<w:t[^>]*>([^<]*)</gs)].map((m) => m[1])
    expect(headings).toEqual(
      expect.arrayContaining([
        'Curriculum Reference',
        'Learning Objectives',
        'Key Words',
        'Starter / Introduction',
        'Main Activities (Development)',
        'Plenary / Conclusion',
        'Assessment',
        'Differentiation / Support',
      ])
    )
  })

  it('prints every phase the plan carries, in order and numbered', async () => {
    const parts = await unzip(await build.lessonPlan())
    const text = [...parts['word/document.xml'].matchAll(/<w:t[^>]*>([^<]*)<\/w:t>/g)].map((m) => m[1])
    const body = text.join('\n')
    for (const item of [...PLAN.starter, ...PLAN.main, ...PLAN.plenary]) expect(body).toContain(item)
    expect(text).toContain('1.  ')
    expect(text).toContain('2.  ')
  })

  it('does not print placeholder timing under every activity', async () => {
    const parts = await unzip(await build.lessonPlan())
    // An earlier version emitted a "⏱ n" line after each activity, where n was
    // just the array index — 12 meaningless lines per plan.
    expect(parts['word/document.xml']).not.toContain('\u23f1')
  })

  it('labels the sections a prefill took from the syllabus template (P1-4)', async () => {
    const parts = await unzip(await build.lessonPlan())
    const plain = parts['word/document.xml']
    // The fixture has no inheritedFields, so nothing is labelled.
    expect(plain).not.toContain('teaching template')

    const inherited = await unzip(await buildPlanWith({
      inheritedFields: ['rpk', 'plenary', 'assessment'],
    }))
    const doc = inherited['word/document.xml']
    const headings = [...doc.matchAll(/<w:pStyle w:val="Heading2"\/><\/w:pPr>(?:(?!<\/w:p>).)*?<w:t[^>]*>([^<]*)</gs)].map((m) => m[1])
    // Only the inherited ones carry the marker; the written activity phases do not.
    // (Compared by prefix: docx escapes the apostrophe in "Let's" as `&apos;`.)
    const labelled = headings.filter((h) => h.includes('(teaching template)'))
    expect(labelled).toHaveLength(3)
    expect(labelled.some((h) => h.startsWith('Relevant Previous Knowledge'))).toBe(true)
    expect(labelled).toContain('Plenary / Conclusion (teaching template)')
    expect(labelled).toContain('Assessment (teaching template)')
    expect(headings).toContain('Starter / Introduction')
    expect(headings).toContain('Main Activities (Development)')
    // …and the document explains the marker rather than leaving it a riddle.
    expect(doc).toContain('Sections marked')
    expect(doc).toContain('teaching template')
  })

  it('leaves the curriculum reference as a table, not run-on prose', async () => {
    const parts = await unzip(await build.lessonPlan())
    const table = /<w:tbl>.*?<\/w:tbl>/s.exec(parts['word/document.xml'])[0]
    expect(table).toContain('Content standard')
    expect(table).toContain('Sub-strand')
    // Borderless: a reference block, not a spreadsheet.
    expect(table).toMatch(/<w:tblBorders><w:top w:val="none"/)
  })
})

describe('scheme layout', () => {
  it('is landscape and prints the term as one wide table', async () => {
    const parts = await unzip(await build.scheme())
    expect(parts['word/document.xml']).toMatch(/w:orient="landscape"/)
    const table = /<w:tbl>.*?<\/w:tbl>/s.exec(parts['word/document.xml'])[0]
    for (const col of ['Wk', 'Strand / Sub-strand', 'Content Standard', 'Indicators', 'Resources']) {
      expect(table).toContain(col)
    }
  })

  it('sizes its columns to the landscape page, not the portrait one', async () => {
    const parts = await unzip(await build.scheme())
    const grid = /<w:tblGrid>(.*?)<\/w:tblGrid>/s.exec(parts['word/document.xml'])[1]
    const widths = [...grid.matchAll(/w:w="(\d+)"/g)].map((m) => Number(m[1]))
    expect(widths).toHaveLength(5)
    // A4 landscape (16838) less the 2 x 1080 twip margins.
    expect(widths.reduce((a, b) => a + b, 0)).toBe(14678)
  })
})
