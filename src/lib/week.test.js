import { describe, expect, it } from 'vitest'
import { isoWeekKey, weekKeyFor, WEEKLY_QUOTA } from './week'

const D = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

describe('isoWeekKey', () => {
  it('matches ISO-8601 reference weeks', () => {
    expect(isoWeekKey(D('2026-01-01'))).toBe('2026-W01') // Thursday
    expect(isoWeekKey(D('2026-01-05'))).toBe('2026-W02') // the following Monday
    expect(isoWeekKey(D('2026-09-18'))).toBe('2026-W38')
  })

  it('puts Sunday in the week that started on Monday', () => {
    expect(isoWeekKey(D('2026-01-04'))).toBe('2026-W01') // Sunday of week 1
    expect(isoWeekKey(D('2026-01-05'))).toBe('2026-W02')
  })

  it('assigns days at the year boundary to the ISO year, not the calendar year', () => {
    // Monday 2025-12-29 belongs to ISO week 2026-W01 …
    expect(isoWeekKey(D('2025-12-29'))).toBe('2026-W01')
    // … and Friday 2027-01-01 belongs to 2026-W53.
    expect(isoWeekKey(D('2027-01-01'))).toBe('2026-W53')
  })

  it('is always two digits, so string sorting is chronological', () => {
    expect(isoWeekKey(D('2026-01-05'))).toMatch(/^\d{4}-W\d{2}$/)
    const keys = [D('2026-01-05'), D('2026-03-02'), D('2026-09-18')].map(isoWeekKey)
    expect([...keys].sort()).toEqual(keys)
  })

  it('does not depend on the time of day', () => {
    const noon = new Date(2026, 8, 18, 12, 30)
    const midnight = new Date(2026, 8, 18, 0, 0)
    expect(isoWeekKey(noon)).toBe(isoWeekKey(midnight))
  })

  it('exposes weekKeyFor as the same function', () => {
    expect(weekKeyFor(D('2026-09-18'))).toBe(isoWeekKey(D('2026-09-18')))
  })

  it('keeps the weekly quota positive', () => {
    expect(WEEKLY_QUOTA).toBeGreaterThan(0)
  })
})
