export const WEEKLY_QUOTA = 10 // questions per member per week (Feed reminder)

/** ISO-8601 week key, e.g. "2026-W38". Stable across time zones for a given date. */
export function isoWeekKey(date = new Date()) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const day = d.getUTCDay() || 7 // Monday = 1 … Sunday = 7
  d.setUTCDate(d.getUTCDate() + 4 - day) // move to the Thursday of this week
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  const week = Math.ceil(((d - yearStart) / 86400000 + 1) / 7)
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`
}

export function weekKeyFor(date) {
  return isoWeekKey(date)
}
