/*
 * The bundle's starter question bank (P1-5).
 *
 * `scripts/generate_question_bank.py` writes practice items and
 * `scripts/build_question_bank.py` validates and serves them as
 * `curriculum/questions/<subject>/<grade>.json` with an index at
 * `curriculum/questions/_index.json`. Nothing in the app could see it, so the
 * question bank opened empty on every install.
 *
 * This module reads the index and a subject-grade file, and turns a selection
 * into the documents the app writes to Firestore — the same shape `QuestionForm`
 * saves, so imported questions behave exactly like hand-written ones.
 */

const BASE_URL = import.meta.env.BASE_URL || '/'

const url = (path) => `${BASE_URL}curriculum/${path}`

/** The bank's coverage index: what exists, per subject and grade. */
export async function loadStarterIndex() {
  try {
    const response = await fetch(url('questions/_index.json'))
    if (!response.ok) return null
    const index = await response.json()
    return index?.built ? index : null
  } catch {
    return null
  }
}

/** One subject-grade's questions, or null when the bank has none. */
export async function loadStarterPack(subjectId, grade) {
  try {
    const response = await fetch(url(`questions/${subjectId}/${grade}.json`))
    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  }
}

/**
 * The Firestore document a starter question becomes.
 *
 * The shape is `QuestionForm`'s payload field for field, so an imported question
 * behaves exactly like a hand-written one — plus provenance: the item's own id
 * and the `source` the generator stamped, so a generated question is never
 * mistaken for a hand-written one, or vice versa. `indicatorIds` is empty on
 * purpose: that array holds whole indicator *records* chosen in the form, and a
 * record is taken from the served curriculum at import time by the caller.
 */
export function starterToFirestore(item, { subjectId, subjectName, grade, authorId, authorName }) {
  return {
    type: item.type || 'short',
    grade,
    subjectId,
    subjectName: subjectName || subjectId,
    term: 1,
    prompt: item.prompt,
    options: item.type === 'mcq' ? item.options || [] : [],
    answer: item.answer ?? '',
    marks: item.marks ?? 1,
    // Kept so a teacher can see which questions a machine wrote and which rule
    // produced them (the bank's filters and the paper's footer both read it).
    source: item.source || 'generated',
    difficulty: item.difficulty || 'core',
    status: 'published',
    explanation: '',
    indicatorIds: [],
    indicatorCodes: [item.indicatorCode],
    starterBankId: item.id,
    authorId,
    authorName: authorName || 'Member',
  }
}
