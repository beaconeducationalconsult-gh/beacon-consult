/*
 * Exam paper composition (P1-5 / the assessment product).
 *
 * `questionPaper.js` prints whatever it is handed. This module decides what to
 * hand it: a paper of a requested size, assembled from the questions a teacher
 * has — their own bank in Firestore plus the served starter bank, which for
 * B7–B9 is now the only content that exists before anyone writes anything.
 *
 * Two rules shape the composition:
 *
 *   1. **A section draws only on its own types.** An objective paper cannot
 *      print an essay in Section A, whatever the marks budget says.
 *   2. **Coverage before depth.** While filling a section, the first item from
 *      each indicator goes in before the second item from any indicator, so a
 *      class paper does not end up testing one sub-strand six times.
 *
 * Everything here is pure: same pool, same paper. That is what lets the exam
 * page show a preview, the teacher drop a question and see the recomposition,
 * and the tests below hold the behaviour without a browser.
 */

/** The shape of a paper, before any questions are chosen. */
export const SECTION_PLAN = [
  {
    id: 'A',
    label: 'Section A — Objectives',
    types: ['mcq'],
    weight: 0.4,
    instructions: 'Answer all the questions in this section. Circle the letter of the correct answer.',
  },
  {
    id: 'B',
    label: 'Section B — Short answers',
    types: ['short', 'truefalse'],
    weight: 0.35,
    instructions: 'Answer all the questions in this section.',
  },
  {
    id: 'C',
    label: 'Section C — Essay',
    types: ['essay'],
    weight: 0.25,
    instructions: 'Answer any two questions in this section.',
  },
]

/** The type a question is treated as when it does not say. */
const typeOf = (question) => question.type || 'short'

/**
 * The indicator a question hangs off.
 *
 * Two shapes live in the app: the served bank's items carry `indicatorCode`
 * (a string), and everything written through `QuestionForm` /
 * `starterToFirestore` carries `indicatorCodes` (an array, because a plan can
 * cite several). A paper that read only one of them would silently treat half
 * its pool as unassigned.
 */
export const indicatorOf = (question) =>
  question?.indicatorCode || question?.indicatorCodes?.[0] || null

/**
 * The indicator codes a term actually schedules (or the whole year for
 * 'all'), read from `public/curriculum/schedules/<grade>-<subject>.json`.
 *
 * This is the curriculum map doing the job only it can do: an end-of-term paper
 * should ask about the term's work, and the schedule is the only thing in the
 * repo that knows which indicators that is. It is deliberately the *scheduled*
 * codes, not every indicator in the grade — a term-2 paper built from the whole
 * grade would test the third term in the second.
 */
export function termScope(lessons = [], term = 'all') {
  const codes = new Set()
  for (const lesson of lessons) {
    if (term !== 'all' && Number(lesson?.term) !== Number(term)) continue
    const code = lesson?.indicatorCode || lesson?.code
    if (code) codes.add(code)
  }
  return codes
}

/** The pool restricted to questions that hang off one of `codes`. */
export function filterByIndicators(pool = [], codes) {
  if (!codes || !codes.size) return pool
  return pool.filter((question) => {
    const code = indicatorOf(question)
    return code ? codes.has(code) : false
  })
}

/**
 * How much of a scope the pool actually covers.
 *
 * `missing` is the honest half and the reason this exists: a teacher about to
 * set an end-of-term paper wants to know *which* scheduled indicators nothing
 * in the bank asks about, not just a percentage.
 */
export function coverageOf(pool = [], codes = new Set()) {
  const covered = new Set()
  for (const question of pool) {
    const code = indicatorOf(question)
    if (code && codes.has(code)) covered.add(code)
  }
  const missing = [...codes].filter((code) => !covered.has(code)).sort()
  return {
    total: codes.size,
    covered: covered.size,
    missing,
    percent: codes.size ? Math.round((covered.size / codes.size) * 100) : 0,
  }
}

const marksOf = (question) => Math.max(1, Number(question.marks) || 1)

/** Which section a question belongs to, or null when the plan has no home for it. */
export function sectionForType(type, plan = SECTION_PLAN) {
  return plan.find((section) => section.types.includes(type)) || null
}

/**
 * Counts for the page's "what is in the pool" line, per section.
 * A question the plan has no section for is still counted, so a teacher sees it.
 */
export function summarise(pool = [], plan = SECTION_PLAN) {
  const bySection = plan.map((section) => {
    const items = pool.filter((q) => section.types.includes(typeOf(q)))
    return {
      id: section.id,
      label: section.label,
      count: items.length,
      marks: items.reduce((sum, q) => sum + marksOf(q), 0),
    }
  })
  const placed = bySection.reduce((sum, section) => sum + section.count, 0)
  return {
    total: pool.length,
    bySection,
    // Types the plan does not place (a free "truefalse" toggle in old data, say).
    unplaced: pool.length - placed,
    marks: pool.reduce((sum, q) => sum + marksOf(q), 0),
  }
}

/**
 * Group the uncovered indicators by the sub-strand they sit in, for the gap
 * line under the coverage count.
 *
 * Naming the sub-strand alone would overstate the gap — a sub-strand can be
 * half covered — so the count travels with the name ("3 in Shape and Space").
 * Distinct codes only: a code appears on several lessons (one per week), and
 * counting lessons would report a gap five times its size.
 */
export function groupMissing(lessons = [], missing = []) {
  const wanted = new Set(missing)
  const byStrand = new Map()
  const seen = new Set()
  for (const lesson of lessons) {
    const code = lesson?.indicatorCode || lesson?.code
    if (!code || !wanted.has(code) || seen.has(code)) continue
    seen.add(code)
    const name = lesson?.subStrandName || lesson?.strandName || 'unscheduled'
    if (!byStrand.has(name)) byStrand.set(name, new Set())
    byStrand.get(name).add(code)
  }
  const groups = [...byStrand.entries()]
    .map(([name, codes]) => ({ name, count: codes.size }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  const unnamed = missing.filter((code) => !seen.has(code))
  if (unnamed.length) groups.push({ name: 'codes the schedule does not name', count: unnamed.length })
  return groups
}

/**
 * Order candidates so coverage comes first: one question per indicator, in a
 * stable order, then the section's remaining depth. Deterministic by design —
 * indicator code, then question id — so the same pool always builds the same
 * paper and a teacher can re-open yesterday's paper.
 */
function spreadByIndicator(candidates) {
  const groups = new Map()
  for (const question of [...candidates].sort((a, b) => {
    const codeA = String(indicatorOf(a) || '')
    const codeB = String(indicatorOf(b) || '')
    if (codeA !== codeB) return codeA < codeB ? -1 : 1
    return String(a.id).localeCompare(String(b.id))
  })) {
    const code = String(indicatorOf(question) || 'unassigned')
    if (!groups.has(code)) groups.set(code, [])
    groups.get(code).push(question)
  }
  const firsts = [...groups.values()].map((group) => group[0])
  const rest = [...groups.values()].flatMap((group) => group.slice(1))
  return [...firsts, ...rest]
}

/**
 * Build a paper from a pool of questions.
 *
 * `targetMarks` is a target, not a promise: each section stops before it would
 * overshoot its share, so the printed total is usually a little under what was
 * asked for — and the page says so rather than quietly rounding up.
 *
 * A section can come back **empty**, and that is a decision, not an oversight:
 * a 20-mark paper cannot carry an 8-mark essay without becoming a 22-mark
 * paper, and printing a paper that is not the one that was asked for is worse
 * than printing a short one. When that happens the section is named in
 * `omitted`, so the page can tell the teacher why (and what to change).
 *
 * One exception keeps a section alive: if the section's own share is smaller
 * than a single question but the *paper* has room, its cheapest question goes
 * in. That is the 60-mark paper whose Section C share is 15 and whose essays
 * are 8 marks each.
 */
export function composePaper(pool = [], { targetMarks = 50, plan = SECTION_PLAN } = {}) {
  const target = Math.max(1, Math.round(Number(targetMarks) || 1))

  const sections = plan.map((section) => {
    const candidates = spreadByIndicator(pool.filter((q) => section.types.includes(typeOf(q))))
    const budget = Math.round(target * section.weight)
    const chosen = []
    let marks = 0

    for (const question of candidates) {
      const cost = marksOf(question)
      if (marks + cost > budget) continue
      chosen.push(question)
      marks += cost
    }

    return {
      id: section.id,
      label: section.label,
      instructions: section.instructions,
      weight: section.weight,
      candidates,
      questions: chosen,
      marks,
    }
  })

  // Keep-alive pass: the paper still has room for a section that its own share
  // could not fit. Cheapest first, in plan order, never past the target.
  const omitted = []
  for (const section of sections) {
    if (section.questions.length || !section.candidates.length) continue
    const cheapest = [...section.candidates].sort(
      (a, b) => marksOf(a) - marksOf(b) || String(a.id).localeCompare(String(b.id))
    )[0]
    const total = sections.reduce((sum, other) => sum + other.marks, 0)
    if (total + marksOf(cheapest) <= target) {
      section.questions = [cheapest]
      section.marks = marksOf(cheapest)
    } else {
      omitted.push({
        id: section.id,
        label: section.label,
        reason: `its shortest question is worth ${marksOf(cheapest)} marks, too much for the ${Math.round(
          target * section.weight
        )} marks left in a ${target}-mark paper`,
      })
    }
  }

  const totalMarks = sections.reduce((sum, section) => sum + section.marks, 0)
  return {
    sections: sections.map(({ candidates: _candidates, ...section }) => section),
    totalMarks,
    targetMarks: target,
    omitted,
    // Flat, in paper order — what the PDF exporter takes.
    questions: sections.flatMap((section) => section.questions),
    indicators: new Set(
      sections.flatMap((section) => section.questions.map(indicatorOf).filter(Boolean))
    ).size,
  }
}

/**
 * The pool a paper draws on: the teacher's own questions first, then the served
 * bank's — an authored question and a starter question with the same indicator
 * are both kept, because one of them may be the better print.
 */
export function buildPool(...sources) {
  const seen = new Set()
  const pool = []
  for (const source of sources) {
    for (const question of source || []) {
      const key = question.id || `${question.indicatorCode}:${question.prompt}`
      if (seen.has(key)) continue
      seen.add(key)
      pool.push(question)
    }
  }
  return pool
}
