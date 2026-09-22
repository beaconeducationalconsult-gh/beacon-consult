import { useState } from 'react'
import { ACADEMIC_YEAR, TERMS, fmtDate, getAcademicStatus, termProgress, termWeek } from '../lib/academicCalendar'
import { GRADES, gradeLabel } from '../lib/grades'
import { useGradeSchedules } from '../hooks/useCurriculum'
import { SkeletonList } from './Skeleton'
import EmptyState from './EmptyState'

/**
 * One term's weeks and what is scheduled in each.
 *
 * Lifted out of `src/pages/Calendar.jsx` when that page was folded into the
 * workspace. The "in session" banner that headed the old page is gone: the
 * workspace rail already carries `TermProgressCard`, which reports the same
 * current-term position, and a page that says it twice reads like a bug.
 *
 * Owns its own grade/term state because it is the only consumer — lift it into
 * props if a second caller ever needs to drive it.
 */
export default function TermCalendar() {
  const [grade, setGrade] = useState('B1')
  const [term, setTerm] = useState(1)
  const { lessons, loading: loadingSchedule, error: scheduleError } = useGradeSchedules(grade)
  const status = getAcademicStatus()
  const selected = TERMS.find((t) => t.term === Number(term))

  const termLessons = (lessons || []).filter((lesson) => Number(lesson.term) === Number(term))
  const byWeek = new Map()
  for (const lesson of termLessons) {
    const week = Number(lesson.week) || 1
    if (!byWeek.has(week)) byWeek.set(week, [])
    byWeek.get(week).push(lesson)
  }

  return (
    <section>
      <div className="mb-4">
        <h2 className="card-title text-lg">Term calendar</h2>
        <p className="card-meta mt-1">
          {ACADEMIC_YEAR} · terms, weeks and what is scheduled for your class.
        </p>
      </div>

      <div className="card mb-6 grid gap-4 p-5 sm:grid-cols-4">
        <div>
          <label className="label-caps" htmlFor="c-grade">Grade</label>
          <select id="c-grade" className="input" value={grade} onChange={(e) => setGrade(e.target.value)}>
            {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
          </select>
        </div>
        <div>
          <label className="label-caps" htmlFor="c-term">Term</label>
          <select id="c-term" className="input" value={term} onChange={(e) => setTerm(e.target.value)}>
            {TERMS.map((t) => <option key={t.term} value={t.term}>{t.label}</option>)}
          </select>
        </div>
        {selected && (
          <div className="sm:col-span-2">
            <p className="label-caps">Dates</p>
            <p className="text-sm text-text">{fmtDate(selected.start)} — {fmtDate(selected.end)}</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.round(termProgress(selected) * 100)}%` }} />
            </div>
          </div>
        )}
      </div>

      {loadingSchedule && <SkeletonList rows={4} />}

      {!loadingSchedule && scheduleError && (
        <EmptyState
          title={`Could not load the ${gradeLabel(grade)} schedule`}
          message="The curriculum schedule could not be fetched. Check your connection and reload."
        />
      )}

      {!loadingSchedule && !scheduleError && lessons.length === 0 && (
        <EmptyState
          title={`No schedule for ${gradeLabel(grade)}`}
          message="Kindergarten grades have no scheduled lessons in the curriculum bundle."
        />
      )}

      {!loadingSchedule && !scheduleError && lessons.length > 0 && (
        <ol className="space-y-3">
          {Array.from({ length: 14 }, (_, i) => i + 1).map((week) => {
            const scheduled = byWeek.get(week) || []
            const isCurrent = status.state === 'in-term' && status.term.term === Number(term) && termWeek(status.term) === week
            return (
              <li key={week} className={`card p-5 ${isCurrent ? 'border-brand-300 ring-1 ring-brand-200' : ''}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="card-title">Week {week}{isCurrent && <span className="chip-brand ml-2">this week</span>}</h3>
                  <span className="card-meta">{scheduled.length} scheduled lesson(s)</span>
                </div>
                {scheduled.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {scheduled.slice(0, 12).map((lesson, index) => (
                      <li key={index} className="text-sm text-text">
                        <span className="font-mono text-xs text-brand-700 dark:text-brand-300">{lesson.indicatorCode || lesson.code}</span>{' '}
                        {lesson.sessionTitle || lesson.indicatorDescription}
                        {lesson.subjectName && <span className="card-meta"> · {lesson.subjectName}</span>}
                      </li>
                    ))}
                    {scheduled.length > 12 && <li className="card-meta">+{scheduled.length - 12} more…</li>}
                  </ul>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
