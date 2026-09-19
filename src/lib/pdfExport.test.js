import { describe, expect, it } from 'vitest'
import JSZip from 'jszip'
import { buildSchemePdf } from './schemePdf'
import { buildLessonPlanPdf } from './lessonPlanPdf'
import { buildQuestionPaper } from './questionPaper'
import { buildLessonSlidesPptx } from './lessonSlidesPptx'
import { buildQuizPptx } from './quizPptx'

/*
 * Smoke tests for the exporters the Word tests do not cover: the PDFs (jsPDF +
 * autoTable) and the slide decks (pptxgenjs).
 *
 * `docxExport.test.js` holds the Word documents to the parts Word obeys; these
 * hold the other two to the parts a reader or a projector obeys. The builders
 * (`buildSchemePdf`, …, rather than `downloadSchemePdf`) exist for this: they
 * return the document, so nothing here needs a DOM or a download.
 *
 * What they can catch, in the "senior engineer's 30 seconds" sense: a PDF that
 * is not a PDF, one that lost its landscape orientation or its page, a deck that
 * is not a valid OOXML zip, a deck whose slide has no text at all, and a table
 * whose rows no longer reach the question list (the count of pages is the only
 * thing that moves when autoTable silently drops rows).
 */

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
    {
      week: 2,
      strandName: 'NUMBER',
      subStrandName: 'Sub-strand B4.1.2',
      contentStandard: 'Demonstrate an understanding of fractions.',
      indicators: 'Compare fractions with the same denominator',
      resources: 'Fraction strips',
    },
  ],
}

const PLAN = {
  subjectId: 'mathematics',
  subjectName: 'Mathematics',
  grade: 'B4',
  term: 1,
  week: 2,
  durationMinutes: 60,
  indicatorCodes: ['B4.1.1.1.3'],
  strandName: 'NUMBER',
  subStrandName: 'Sub-strand B4.1.1',
  contentStandard: 'Demonstrate an understanding of quantities and place value.',
  indicatorDescription: 'Identify numbers in different positions around a given number',
  performanceIndicator: 'By the end of the lesson, learners will be able to identify numbers',
  keywords: ['place value', 'numeration'],
  resources: ['NaCCA approved textbook'],
  rpk: 'Learners used number charts in Basic 3.',
  starter: ['Greet learners; mental maths drill.'],
  main: ['ACTIVITY 1: Teacher models with manipulatives.'],
  plenary: ['Quick-fire oral quiz.'],
  assessment: 'Class exercises; oral questions.',
  objectives: ['read and write multi-digit numerals in words and figures'],
}

const QUESTIONS = [
  { id: 'q1', type: 'mcq', prompt: 'How many hundreds are in 4 520?', options: ['4', '45', '452', '4520'], answer: '45', marks: 1 },
  { id: 'q2', type: 'short', prompt: 'Write 7 306 in words.', answer: 'Seven thousand three hundred and six', marks: 2 },
  { id: 'q3', type: 'essay', prompt: 'Explain place value with two examples.', marks: 5 },
]

const DECK = {
  subjectId: 'mathematics',
  subjectName: 'Mathematics',
  grade: 'B4',
  term: 1,
  week: 2,
  slides: [
    { title: 'Place value', indicator: 'B4.1.1.1.3', objectives: ['Read numerals up to 100 000'], steps: ['Warm-up', 'Guided practice'], assessment: 'Name the value of 6 in 3 640', keywords: ['place value'] },
    { title: 'Comparing numbers', objectives: ['Compare two 5-digit numerals'], steps: ['Pair work'], keywords: ['greater than'] },
  ],
}

/** jsPDF documents are byte strings ending in %%EOF; check the container first. */
const pdfBytes = (doc) => Buffer.from(doc.output('arraybuffer'))

const pdf = (doc) => ({
  bytes: pdfBytes(doc),
  header: pdfBytes(doc).subarray(0, 5).toString('latin1'),
  pages: doc.getNumberOfPages(),
  width: Math.round(doc.internal.pageSize.getWidth()),
  height: Math.round(doc.internal.pageSize.getHeight()),
})

/** pptxgenjs → unzipped OOXML parts, keyed by path. */
async function deckParts(pptx) {
  const zip = await JSZip.loadAsync(Buffer.from(await pptx.write({ outputType: 'arraybuffer' })))
  const parts = {}
  for (const name of Object.keys(zip.files)) {
    if (name.endsWith('.xml')) parts[name] = await zip.files[name].async('string')
  }
  return parts
}

const slideText = (parts, n) =>
  [...(parts[`ppt/slides/slide${n}.xml`] || '').matchAll(/<a:t>([^<]*)<\/a:t>/g)].map((m) => m[1]).join(' ')

describe('the PDF exporters', () => {
  it('produce a real PDF', () => {
    for (const doc of [buildSchemePdf(SCHEME), buildLessonPlanPdf(PLAN), buildQuestionPaper(QUESTIONS)]) {
      const out = pdf(doc)
      expect(out.header).toBe('%PDF-')
      expect(out.bytes.length).toBeGreaterThan(1000)
      expect(out.bytes.subarray(-6).toString('latin1').trimEnd()).toMatch(/%%EOF$/)
    }
  })

  it('lay the scheme out in landscape A4 and the plan in portrait', () => {
    expect(pdf(buildSchemePdf(SCHEME))).toMatchObject({ width: 842, height: 595 })
    expect(pdf(buildLessonPlanPdf(PLAN))).toMatchObject({ width: 595, height: 842 })
    expect(pdf(buildQuestionPaper(QUESTIONS))).toMatchObject({ width: 595, height: 842 })
  })

  it('carry the scheme rows and the plan onto the page', () => {
    // A scheme is one landscape page for a term's worth of rows; a plan with all
    // its phases runs to two. The exact count is the only signal that autoTable
    // still found the rows at all.
    expect(pdf(buildSchemePdf(SCHEME)).pages).toBe(1)
    expect(pdf(buildLessonPlanPdf(PLAN)).pages).toBeGreaterThanOrEqual(1)
  })

  it('give the question paper a marking scheme page when answers exist', () => {
    const withAnswers = buildQuestionPaper(QUESTIONS, { subjectName: 'Mathematics', grade: 'B4', term: 1, totalMarks: 8 })
    const withoutAnswers = buildQuestionPaper(QUESTIONS, { subjectName: 'Mathematics', grade: 'B4', term: 1, totalMarks: 8, includeAnswers: false })
    // Two answers → the marking scheme gets its own page.
    expect(pdf(withAnswers).pages).toBeGreaterThan(pdf(withoutAnswers).pages)
  })

  it('survive an empty selection instead of throwing', () => {
    // The pages guard on `.length`; an empty scheme or selection must still make
    // a one-page document, because the button is reachable before data loads.
    expect(pdf(buildSchemePdf({ subjectId: 'mathematics', grade: 'B4', term: 1, rows: [] })).pages).toBe(1)
    expect(pdf(buildQuestionPaper([])).pages).toBe(1)
  })
})

describe('the slide exporters', () => {
  it('write a valid deck package', async () => {
    const parts = await deckParts(buildLessonSlidesPptx(DECK))
    const presentation = parts['ppt/presentation.xml']
    expect(presentation).toBeTruthy()
    // Every slide has to be registered in <p:sldIdLst>, or PowerPoint opens an
    // empty deck even though the slide parts are in the package.
    const registered = [...presentation.matchAll(/<p:sldId /g)].length
    const onDisk = Object.keys(parts).filter((p) => /^ppt\/slides\/slide\d+\.xml$/.test(p)).length
    expect(registered).toBe(onDisk)
    expect(onDisk).toBeGreaterThanOrEqual(3)
  })

  it('give the lesson deck a cover plus one slide per lesson', async () => {
    const parts = await deckParts(buildLessonSlidesPptx(DECK))
    // Cover + one slide per lesson (this exporter adds no closing slide).
    const slides = Object.keys(parts).filter((p) => /^ppt\/slides\/slide\d+\.xml$/.test(p))
    expect(slides.length).toBe(1 + DECK.slides.length)
    const all = slides.map((p) => parts[p]).join(' ')
    for (const text of ['Place value', 'Comparing numbers', 'Pair work']) {
      expect(all, `the deck lost "${text}"`).toContain(text)
    }
    expect(slideText(parts, 1)).toContain('Beacon Educational Consult')
  })

  it('give the quiz deck a cover, a question slide and an answer slide', async () => {
    const parts = await deckParts(buildQuizPptx(QUESTIONS, { subjectName: 'Mathematics', grade: 'B4', term: 1, title: 'Class quiz' }))
    expect(slideText(parts, 1)).toContain('Class quiz')
    const all = Object.keys(parts).map((p) => parts[p]).join(' ')
    expect(all).toContain('How many hundreds are in 4 520?')
    expect(all).toContain('Seven thousand three hundred and six')
    // The cover of this deck is the author string, not the title (the title is
    // the first slide's heading).
    expect(slideText(parts, 2)).toContain('Question 1')
  })

  it('survive a deck with no slides', async () => {
    const parts = await deckParts(buildLessonSlidesPptx({ subjectId: 'mathematics', grade: 'B4', term: 1, week: 1, slides: [] }))
    expect(Object.keys(parts)).toContain('ppt/presentation.xml')
  })
})
