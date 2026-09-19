import PptxGenJS from 'pptxgenjs'
import { gradeLabel } from './grades'

/**
 * Build a teaching deck straight from the curriculum schedule for a week.
 * One slide per lesson: objective, key words, the activity steps we hold, and
 * a closing assessment question.
 */
export function buildLessonSlidesPptx(deck, { school } = {}) {
  const pptx = new PptxGenJS()
  pptx.layout = 'LAYOUT_16x9'
  pptx.author = 'Beacon Educational Consult'
  pptx.title = `${deck.subjectName || deck.subjectId} — ${gradeLabel(deck.grade)} week ${deck.week}`

  const cover = pptx.addSlide()
  cover.background = { color: '4F46E5' }
  cover.addText(deck.subjectName || deck.subjectId, { x: 0.6, y: 1.7, w: 8.8, h: 0.9, fontSize: 38, bold: true, color: 'FFFFFF' })
  cover.addText(`${gradeLabel(deck.grade)} · Term ${deck.term} · Week ${deck.week}`, {
    x: 0.6, y: 2.7, w: 8.8, h: 0.6, fontSize: 20, color: 'E0E7FF',
  })
  if (school) cover.addText(school, { x: 0.6, y: 3.4, w: 8.8, h: 0.5, fontSize: 14, color: 'C7D2FE' })
  cover.addText('Beacon Educational Consult', { x: 0.6, y: 4.9, w: 8.8, h: 0.4, fontSize: 11, color: 'C7D2FE' })

  const slides = deck.slides || []
  slides.forEach((slide, index) => {
    const s = pptx.addSlide()
    s.addText(slide.title || `Lesson ${index + 1}`, {
      x: 0.5, y: 0.4, w: 9, h: 0.7, fontSize: 28, bold: true, color: '0F172A',
    })
    if (slide.indicator) {
      s.addText(slide.indicator, { x: 0.5, y: 1.1, w: 9, h: 0.4, fontSize: 12, color: '4F46E5' })
    }

    let y = 1.6
    if (slide.objectives?.length) {
      s.addText('Learning objectives', { x: 0.5, y, w: 9, h: 0.35, fontSize: 14, bold: true, color: '64748B' })
      y += 0.45
      s.addText(
        slide.objectives.map((line) => ({ text: `• ${line}\n`, options: { breakLine: true } })),
        { x: 0.7, y, w: 8.6, h: 0.4 + slide.objectives.length * 0.35, fontSize: 16, color: '334155' }
      )
      y += 0.5 + slide.objectives.length * 0.35
    }

    const steps = slide.steps || []
    if (steps.length) {
      s.addText('Activities', { x: 0.5, y, w: 9, h: 0.35, fontSize: 14, bold: true, color: '64748B' })
      y += 0.45
      s.addText(
        steps.slice(0, 6).map((line, i) => ({ text: `${i + 1}. ${line}\n`, options: { breakLine: true } })),
        { x: 0.7, y, w: 8.6, h: 0.4 + Math.min(steps.length, 6) * 0.35, fontSize: 15, color: '334155' }
      )
      y += 0.5 + Math.min(steps.length, 6) * 0.35
    }

    if (slide.assessment) {
      s.addText(`Check: ${slide.assessment}`, { x: 0.5, y: Math.min(y, 4.6), w: 9, h: 0.8, fontSize: 14, italic: true, color: 'B45309' })
    }

    if (slide.keywords?.length) {
      s.addText(slide.keywords.join('  ·  '), { x: 0.5, y: 5.0, w: 9, h: 0.4, fontSize: 12, color: '94A3B8' })
    }
  })

  return pptx
}

/** Teaching deck → PPTX download (client-side). */
export async function downloadLessonSlidesPptx(deck, meta = {}) {
  await buildLessonSlidesPptx(deck, meta)
    .writeFile({ fileName: `Slides_${deck.subjectId || 'lesson'}_${deck.grade}_T${deck.term}_W${deck.week}.pptx` })
}
