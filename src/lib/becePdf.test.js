import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { composeBecePaper } from './becePaper'
import { buildBecePaper } from './becePdf'

/*
 * The BECE mock's PDF, held to what a reader and an invigilator obey.
 *
 * Same seam as pdfExport.test.js: the builder returns the document, so nothing
 * here needs a DOM. What can go quietly wrong — a file that is not a PDF, a
 * rubric that drifted off the paper, a marking scheme that stopped being
 * included — is what these assert.
 */

const PACKS = ['B7', 'B8', 'B9'].map((grade) => ({
  grade,
  items: JSON.parse(
    readFileSync(new URL(`../../public/curriculum/questions/mathematics/${grade}.json`, import.meta.url), 'utf8'),
  ).items,
}))

const PAPER = composeBecePaper(PACKS)

const outputOf = (doc) => {
  const buffer = doc.output('arraybuffer')
  return {
    bytes: new Uint8Array(buffer),
    text: Buffer.from(buffer).toString('latin1'),
  }
}

describe('the BECE paper PDF', () => {
  const student = buildBecePaper(PAPER, { includeAnswers: false })
  const teacher = buildBecePaper(PAPER, { includeAnswers: true })
  const { bytes, text } = outputOf(student)

  it('is a real PDF', () => {
    expect(text.slice(0, 5)).toBe('%PDF-')
    expect(text.trimEnd().endsWith('%%EOF')).toBe(true)
    expect(bytes.length).toBeGreaterThan(20_000) // 40 questions with options, not a stub
  })

  it('carries both papers and their rubrics', () => {
    // Read as ASCII-safe fragments: jsPDF escapes parentheses in the content
    // stream and maps em-dashes out of latin1, so the raw bytes of the real
    // strings are not what a byte-level read of the file sees.
    expect(text).toContain('PAPER 1')
    expect(text).toContain('PAPER 2')
    expect(text).toContain('Answer ALL the questions')
    expect(text).toContain('questions only')
    expect(text).toContain('BECE Mock Examination')
  })

  it('prints the student copy without answers', () => {
    expect(text).not.toContain('Marking scheme')
  })

  it('gives the teacher copy the marking scheme, and it costs pages', () => {
    expect(outputOf(teacher).text).toContain('Marking scheme')
    expect(teacher.internal.getNumberOfPages()).toBeGreaterThan(student.internal.getNumberOfPages())
  })

  it('prints every Paper 2 question and its lettered parts', () => {
    const teacherText = outputOf(teacher).text
    for (const question of PAPER.paper2.questions) {
      expect(teacherText).toContain(`Question ${question.number}`)
      for (const part of question.parts) {
        expect(teacherText).toContain(`(${part.letter})`)
      }
    }
  })

  it('names the school that asked for it', () => {
    const bespoke = outputOf(buildBecePaper(PAPER, { school: 'Accra Grammar School', includeAnswers: false }))
    expect(bespoke.text).toContain('Accra Grammar School')
  })
})
