/**
 * Ghana basic-school academic calendar. Static and pure so it works offline
 * and drives the Feed/Calendar widgets without a network round trip.
 *
 * Update the term dates each academic year — this is the only place they live.
 */
export const ACADEMIC_YEAR = '2026/2027'

export const TERMS = [
  {
    term: 1,
    label: 'Term 1',
    start: '2026-09-08',
    end: '2026-12-18',
    weeks: 14,
    note: 'Reopening and first-term assessments',
  },
  {
    term: 2,
    label: 'Term 2',
    start: '2027-01-12',
    end: '2027-04-01',
    weeks: 12,
    note: 'Second-term work and mid-year examinations',
  },
  {
    term: 3,
    label: 'Term 3',
    start: '2027-04-20',
    end: '2027-07-24',
    weeks: 13,
    note: 'Third-term work, BECE and end-of-year assessments',
  },
]

const DAY = 86400000
const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate())

export function fmtDate(value) {
  if (!value) return ''
  // Firestore Timestamps, Dates and ISO strings all arrive here.
  const date = typeof value?.toDate === 'function' ? value.toDate() : value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date?.getTime?.())) return ''
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Kept out of component bodies so render stays pure. */
export const currentYear = () => new Date().getFullYear()

/**
 * Whole days from `from` (default: now) until `value`. Negative once past.
 *
 * `from` is explicit so callers that already know "now" — and tests — do not
 * silently measure against the real clock.
 */
export function daysUntil(value, from = new Date()) {
  const target = startOfDay(value instanceof Date ? value : new Date(value))
  return Math.round((target - startOfDay(from)) / DAY)
}

/** Where we are in the school year: in term, on holiday, or before it starts. */
export function getAcademicStatus(today = new Date()) {
  const now = startOfDay(today)
  for (const term of TERMS) {
    const start = startOfDay(new Date(term.start))
    const end = startOfDay(new Date(term.end))
    if (now >= start && now <= end) {
      return { state: 'in-term', term, daysUntilStart: 0, daysRemaining: Math.round((end - now) / DAY) }
    }
    if (now < start) {
      // Measured from the `today` this call was given, not from the real clock.
      return { state: 'before-term', term, daysUntilStart: Math.round((start - now) / DAY), daysRemaining: 0 }
    }
  }
  return { state: 'holiday', term: null, daysUntilStart: null, daysRemaining: 0, next: TERMS[0] }
}

/** 0…1 progress through a term, clamped. */
export function termProgress(term, today = new Date()) {
  if (!term) return 0
  const start = startOfDay(new Date(term.start))
  const end = startOfDay(new Date(term.end))
  const now = startOfDay(today)
  if (now <= start) return 0
  if (now >= end) return 1
  return (now - start) / (end - start)
}

/** Week number of the term a date falls in (1-based), or null when outside. */
export function termWeek(term, today = new Date()) {
  if (!term) return null
  const start = startOfDay(new Date(term.start))
  const now = startOfDay(today)
  const days = Math.floor((now - start) / DAY)
  if (days < 0) return null
  return Math.floor(days / 7) + 1
}
