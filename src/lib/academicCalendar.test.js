import { describe, expect, it } from 'vitest'
import { daysUntil, fmtDate, getAcademicStatus, termProgress, termWeek, TERMS } from './academicCalendar'

const D = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

describe('getAcademicStatus', () => {
  it('reports the term a date falls inside', () => {
    const status = getAcademicStatus(D('2026-09-18'))
    expect(status.state).toBe('in-term')
    expect(status.term.term).toBe(1)
    expect(status.daysRemaining).toBe(91) // to 2026-12-18 inclusive
  })

  it('treats the first and last day of a term as in-term', () => {
    expect(getAcademicStatus(D('2026-09-08')).state).toBe('in-term')
    expect(getAcademicStatus(D('2026-12-18')).state).toBe('in-term')
    expect(getAcademicStatus(D('2026-12-18')).daysRemaining).toBe(0)
  })

  // Regression: daysUntilStart used to read the real clock instead of the date
  // passed in, so a before-term date could report a negative countdown.
  it('counts down to the next term from the date given, never negatively', () => {
    const beforeTerm1 = getAcademicStatus(D('2026-08-01'))
    expect(beforeTerm1.state).toBe('before-term')
    expect(beforeTerm1.term.term).toBe(1)
    expect(beforeTerm1.daysUntilStart).toBe(38) // 2026-08-01 → 2026-09-08

    const betweenTerms = getAcademicStatus(D('2026-12-19'))
    expect(betweenTerms.state).toBe('before-term')
    expect(betweenTerms.term.term).toBe(2)
    expect(betweenTerms.daysUntilStart).toBe(24) // 2026-12-19 → 2027-01-12
  })

  it('reports a holiday once the last term has ended', () => {
    const status = getAcademicStatus(D('2027-08-01'))
    expect(status.state).toBe('holiday')
    expect(status.term).toBeNull()
    expect(status.next).toBe(TERMS[0])
  })
})

describe('termProgress', () => {
  const term1 = TERMS[0]

  it('clamps to 0 before the term and 1 after it', () => {
    expect(termProgress(term1, D('2026-09-01'))).toBe(0)
    expect(termProgress(term1, D('2027-01-01'))).toBe(1)
  })

  it('is a fraction in between', () => {
    const mid = termProgress(term1, D('2026-10-29'))
    expect(mid).toBeGreaterThan(0)
    expect(mid).toBeLessThan(1)
  })

  it('handles a missing term', () => {
    expect(termProgress(null)).toBe(0)
  })
})

describe('termWeek', () => {
  const term1 = TERMS[0]

  it('is 1-based from the first day', () => {
    expect(termWeek(term1, D('2026-09-08'))).toBe(1)
    expect(termWeek(term1, D('2026-09-16'))).toBe(2)
  })

  it('is null before the term starts and for a missing term', () => {
    expect(termWeek(term1, D('2026-09-01'))).toBeNull()
    expect(termWeek(null, D('2026-09-01'))).toBeNull()
  })
})

describe('daysUntil', () => {
  it('measures from the reference date when given one', () => {
    expect(daysUntil(D('2026-09-18'), D('2026-09-08'))).toBe(10)
    expect(daysUntil(D('2026-09-08'), D('2026-09-18'))).toBe(-10)
  })

  it('accepts a date string, which is what Firestore stores', () => {
    expect(daysUntil('2026-09-18', D('2026-09-08'))).toBe(10)
  })
})

describe('fmtDate', () => {
  it('formats dates, timestamps and ISO strings', () => {
    expect(fmtDate(D('2026-09-08'))).toBe('8 Sept 2026')
    expect(fmtDate('2026-09-08')).toBe('8 Sept 2026')
    expect(fmtDate({ toDate: () => D('2026-09-08') })).toBe('8 Sept 2026')
  })

  it('returns an empty string rather than "Invalid Date"', () => {
    expect(fmtDate(null)).toBe('')
    expect(fmtDate(undefined)).toBe('')
    expect(fmtDate('nonsense')).toBe('')
  })
})
