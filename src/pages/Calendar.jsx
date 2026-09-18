import { useState } from 'react'
import { ACADEMIC_YEAR, TERMS, fmtDate, getAcademicStatus, termProgress, termWeek } from '../lib/academicCalendar'
import { GRADES, gradeLabel } from '../lib/grades'
import { useSchedules } from '../hooks/useCurriculum'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'

/** Term calendar for a class, merged with the department's static calendar. */
export default function Calendar() {
  const [grade, setGrade] = useState('B1')
  const [term, setTerm] = useState(1)
  const { lessons, loading: loadingSchedule, error: scheduleError } = useSchedules(grade)
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
    <div>
      <header className="mb-6">
        <h1 className="page-title">Calendar</h1>
        <p className="page-subtitle">{ACADEMIC_YEAR} · terms, weeks and what is scheduled for your class.</p>
      </header>

      {status.state === 'in-term' && (
        <div className="card mb-6 border-l-4 border-l-emerald-500 p-5">
          <p className="section-heading">In session</p>
          <p className="mt-1 text-sm text-slate-700">
            {status.term.label} · week {termWeek(status.term)} of {status.term.weeks} · {status.daysRemaining} days remaining
          </p>
        </div>
      )}

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
            <p className="text-sm text-slate-700">{fmtDate(selected.start)} — {fmtDate(selected.end)}</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
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
                <h2 className="card-title">Week {week}{isCurrent && <span className="chip-brand ml-2">this week</span>}</h2>
                <span className="card-meta">{scheduled.length} scheduled lesson(s)</span>
              </div>
              {scheduled.length > 0 && (
                <ul className="mt-3 space-y-1">
                  {scheduled.slice(0, 12).map((lesson, index) => (
                    <li key={index} className="text-sm text-slate-600">
                      <span className="font-mono text-xs text-brand-700">{lesson.indicatorCode || lesson.code}</span>{' '}
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
    </div>
  )
}
