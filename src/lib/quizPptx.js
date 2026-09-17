import PptxGenJS from 'pptxgenjs'
import { gradeLabel } from './grades'

/**
 * Classroom quiz slideshow (PPTX, client-side).
 * One slide per question, answer revealed on the next slide.
 */
export async function downloadQuizPptx(
  questions,
  { subjectName, grade, term, title = 'Class Quiz' } = {}
) {
  const pptx = new PptxGenJS()
  pptx.layout = 'LAYOUT_16x9'
  pptx.author = 'Beacon Educational Consult'
  pptx.title = `${title} — ${subjectName || ''} ${grade || ''}`

  const cover = pptx.addSlide()
  cover.background = { color: '4F46E5' }
  cover.addText(title, { x: 0.6, y: 1.9, w: 8.8, h: 1, fontSize: 40, bold: true, color: 'FFFFFF' })
  cover.addText(
    [subjectName, gradeLabel(grade), term ? `Term ${term}` : null].filter(Boolean).join(' · '),
    { x: 0.6, y: 3.0, w: 8.8, h: 0.6, fontSize: 18, color: 'E0E7FF' }
  )
  cover.addText('Beacon Educational Consult', { x: 0.6, y: 4.9, w: 8.8, h: 0.4, fontSize: 12, color: 'C7D2FE' })

  questions.forEach((q, index) => {
    const slide = pptx.addSlide()
    slide.addText(`Question ${index + 1}`, {
      x: 0.5, y: 0.35, w: 9, h: 0.4, fontSize: 12, bold: true, color: '64748B',
    })
    slide.addText(q.prompt || q.question || '', {
      x: 0.5, y: 0.85, w: 9, h: 1.5, fontSize: 24, bold: true, color: '0F172A',
    })

    if (q.type === 'mcq' && q.options?.length) {
      slide.addText(
        q.options.map((opt, i) => ({ text: `${String.fromCharCode(65 + i)}.  ${opt}\n`, options: { breakLine: true } })),
        { x: 0.9, y: 2.5, w: 8.2, h: 2.3, fontSize: 18, color: '334155' }
      )
    }

    slide.addText(`${q.marks ?? 1} mark(s)`, {
      x: 0.5, y: 5.0, w: 9, h: 0.35, fontSize: 12, color: '94A3B8',
    })

    if (q.answer) {
      const answer = pptx.addSlide()
      answer.addText('Answer', { x: 0.5, y: 0.35, w: 9, h: 0.4, fontSize: 12, bold: true, color: 'B45309' })
      answer.addText(q.answer, { x: 0.5, y: 1.6, w: 9, h: 2, fontSize: 28, bold: true, color: '065F46' })
    }
  })

  await pptx.writeFile({ fileName: `Quiz_${subjectName || 'quiz'}_${grade || ''}_T${term || ''}.pptx` })
}
