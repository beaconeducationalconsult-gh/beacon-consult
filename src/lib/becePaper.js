/*
 * BECE mock composition — mathematics B7–B9.
 *
 * The West African Examinations Council's BECE mathematics paper, as confirmed
 * for the Common Core (the B7–B9 slice of the Standards-Based Curriculum this
 * bundle serves — WAEC's 2024 scheme and the 2026 guides agree on the shape):
 *
 *   Paper 1 — 40 compulsory objective questions, 1 hour, 40 marks (1 each).
 *   Paper 2 — 6 essay questions, answer any four, 1 hour, 60 marks (15 each).
 *   Both papers at one sitting, 100 marks in all.
 *
 * The served bank holds neither 15-mark essays nor ready-made "Paper 2"
 * questions — its JHS items are 1–5 marks — so a Paper 2 question is composed
 * the way the real ones are printed: a small set of parts, (a), (b), (c)…,
 * whose marks add to exactly 15. Parts come from one strand of one grade where
 * the marks allow, spilling into a neighbouring sub-strand before anything
 * else, so a question reads as one topic the way the real paper's do.
 *
 * Everything here is pure and deterministic: same banks, same paper. That is
 * what lets the preview, the PDF and a re-opened page agree, and what lets the
 * tests hold the composition to the real bundle.
 */

/** The exam WAEC actually sets, as this module builds it. */
export const BECE_FORMAT = {
  paper1: { count: 40, marksEach: 1, minutes: 60 },
  paper2: { count: 6, answerCount: 4, marksEach: 15, minutes: 60 },
  totalMarks: 100,
}

const GRADE_ORDER = ['B7', 'B8', 'B9']

const strandOf = (code) => String(code || '').match(/^[^.]+\.[^.]+/)?.[0] || null
const marksOf = (question) => Math.max(1, Number(question.marks) || 1)

/**
 * Paper 1 — `count` objective questions off the whole JHS bank.
 *
 * Each grade's MCQs are ordered one-per-indicator-first (the coverage sweep
 * examPaper.js uses), then the grades are read round-robin, so the paper is
 * balanced across the three years and no indicator is asked twice before any
 * is asked once. Deterministic throughout.
 */
export function composePaper1(packs = [], count = BECE_FORMAT.paper1.count) {
  const queues = packs.map((pack) => {
    const mcq = (pack.items || [])
      .filter((item) => item.type === 'mcq')
      .sort((a, b) =>
        String(a.indicatorCode || '').localeCompare(String(b.indicatorCode || '')) ||
        String(a.id).localeCompare(String(b.id)))
    const byIndicator = new Map()
    for (const item of mcq) {
      const code = item.indicatorCode || 'unassigned'
      if (!byIndicator.has(code)) byIndicator.set(code, [])
      byIndicator.get(code).push(item)
    }
    const groups = [...byIndicator.values()]
    return [...groups.map((group) => group[0]), ...groups.flatMap((group) => group.slice(1))]
  })

  const questions = []
  let turn = 0
  while (questions.length < count && queues.some((queue) => queue.length)) {
    const queue = queues[turn % queues.length]
    if (queue.length) questions.push(queue.shift())
    turn += 1
  }

  const gradeSpread = {}
  for (const question of questions) {
    const grade = question.id?.split('.')[0] || '?'
    gradeSpread[grade] = (gradeSpread[grade] || 0) + 1
  }

  return {
    questions,
    marks: questions.length * BECE_FORMAT.paper1.marksEach,
    minutes: BECE_FORMAT.paper1.minutes,
    gradeSpread,
    indicators: new Set(questions.map((q) => q.indicatorCode).filter(Boolean)).size,
    shortfall: questions.length < count
      ? `the JHS bank holds ${questions.length} objective questions — ${count - questions.length} short of the ${count} Paper 1 asks for`
      : null,
  }
}

/**
 * The exact-`target` subset of `items`, fewest parts first.
 *
 * A BECE question part is worth 2–6 marks and a question has 3–5 of them, so
 * the search prefers 4 parts and only opens a fifth when nothing tighter
 * reaches the target. Items are read longest-first (an essay carrying 5 marks
 * is the natural opening part), ties by id — so the same pool always yields
 * the same question.
 */
function exactSubset(items, target, maxParts = 4) {
  const sorted = [...items].sort((a, b) =>
    marksOf(b) - marksOf(a) || String(a.id).localeCompare(String(b.id)))

  const walk = (start, need, acc) => {
    if (need === 0) return acc.length ? acc : null
    if (acc.length >= maxParts || start >= sorted.length) return null
    for (let i = start; i < sorted.length; i += 1) {
      if (marksOf(sorted[i]) > need) continue
      const found = walk(i + 1, need - marksOf(sorted[i]), [...acc, sorted[i]])
      if (found) return found
    }
    return null
  }

  return walk(0, target, []) || (maxParts < 5 ? exactSubset(items, target, 5) : null)
}

/**
 * Paper 2 — `count` structured questions of exactly `marksEach` marks.
 *
 * Short-answer and essay items are bucketed by grade + strand; every bucket
 * deep enough to reach the target yields a candidate question (a subset of its
 * items, each used at most once anywhere in the mock). Candidates are then
 * chosen round-robin across the grades, so one deep year cannot crowd the
 * others out, and the parts are lettered easiest-first the way the print does.
 */
export function composePaper2(packs = [], { count = BECE_FORMAT.paper2.count, marksEach = BECE_FORMAT.paper2.marksEach } = {}) {
  const buckets = new Map()
  for (const pack of packs) {
    for (const item of pack.items || []) {
      if (item.type === 'mcq') continue
      const strand = strandOf(item.indicatorCode)
      if (!strand) continue
      const key = `${pack.grade}:${strand}`
      if (!buckets.has(key)) buckets.set(key, { grade: pack.grade, strand, items: [] })
      buckets.get(key).items.push(item)
    }
  }

  const perGrade = { B7: [], B8: [], B9: [] }
  for (const bucket of [...buckets.values()].sort((a, b) => a.key && String(a.strand).localeCompare(String(b.strand)))) {
    if (!perGrade[bucket.grade]) continue
    if (bucket.items.reduce((sum, item) => sum + marksOf(item), 0) < marksEach) continue
    const fresh = bucket.items
    const parts = exactSubset(fresh, marksEach)
    if (!parts) continue
    perGrade[bucket.grade].push({ bucket, parts })
  }

  const candidates = []
  for (let round = 0; round < Math.max(...GRADE_ORDER.map((g) => perGrade[g]?.length || 0), 0); round += 1) {
    for (const grade of GRADE_ORDER) {
      const candidate = perGrade[grade]?.[round]
      if (candidate) candidates.push(candidate)
    }
  }

  const questions = []
  for (const { bucket, parts } of candidates.slice(0, count)) {
    const ordered = [...parts].sort((a, b) =>
      marksOf(a) - marksOf(b) || String(a.id).localeCompare(String(b.id)))
    questions.push({
      id: `bece-p2-${ordered.map((p) => p.id).join('+')}`,
      number: questions.length + 1,
      marks: ordered.reduce((sum, p) => sum + marksOf(p), 0),
      strand: bucket.strand,
      grade: bucket.grade,
      parts: ordered.map((part, index) => ({
        letter: String.fromCharCode(97 + index),
        marks: marksOf(part),
        question: part,
      })),
    })
  }

  return {
    questions,
    answerCount: BECE_FORMAT.paper2.answerCount,
    // What the sitting counts, not what the sheet prints: candidates answer
    // `answerCount` of the six printed questions, so Paper 2 contributes
    // 4 × 15 = 60 of the exam's 100 — the sheet offers 90. Kept apart so the
    // page can say both honestly.
    marks: Math.min(questions.length, BECE_FORMAT.paper2.answerCount) * marksEach,
    printed: questions.reduce((sum, q) => sum + q.marks, 0),
    minutes: BECE_FORMAT.paper2.minutes,
    shortfall: questions.length < count
      ? `the JHS bank composes ${questions.length} of the ${count} structured questions Paper 2 prints — the strands that ran thin are left out rather than padded`
      : null,
  }
}

/**
 * The whole mock, from the three served JHS packs (`loadStarterPack` shapes:
 * `{ grade, items }`). Nothing is written anywhere — the paper is a document,
 * and the page hands it straight to the printer.
 */
export function composeBecePaper(packs = [], options = {}) {
  const paper1 = composePaper1(packs, options.paper1Count)
  const paper2 = composePaper2(packs, options.paper2)

  return {
    subjectId: 'mathematics',
    subjectName: 'Mathematics',
    paper1,
    paper2,
    totalMarks: paper1.marks + paper2.marks,
    indicators: new Set([
      ...paper1.questions.map((q) => q.indicatorCode),
      ...paper2.questions.flatMap((q) => q.parts.map((p) => p.question.indicatorCode)),
    ].filter(Boolean)).size,
    shortfalls: [paper1.shortfall, paper2.shortfall].filter(Boolean),
  }
}
