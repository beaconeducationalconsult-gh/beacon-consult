import { Link, useParams } from 'react-router-dom'
import { useCurriculum } from '../hooks/useCurriculum'
import { SkeletonGrid } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import SubjectIcon from '../components/SubjectIcon'
import { gradeBand, gradeLabel } from '../lib/grades'

/**
 * The subjects of one grade — the level between the grade grid and the
 * strand/sub-strand/indicator browser.
 *
 * `/portal/curriculum/:gradeId` used to be routed straight to `SubjectBrowser`,
 * which expected a *subject* id. Clicking "Basic 4" therefore looked up a
 * subject called "B4" in a hard-coded Basic 1 list, matched nothing, and showed
 * an empty browser for every grade. Both ids now live in the URL:
 *
 *   /portal/curriculum                                → grade grid
 *   /portal/curriculum/B4                             → this page
 *   /portal/curriculum/B4/mathematics                 → SubjectBrowser
 */
export default function GradeSubjects() {
  const { gradeId } = useParams()
  // Grade ids are upper-case (B4, KG1); a hand-typed lower-case URL still works.
  const grade = String(gradeId || '').toUpperCase()
  const { loading, subjects, indicators, error } = useCurriculum(grade)

  const counts = new Map()
  for (const indicator of indicators) {
    if (!indicator.subjectId) continue
    counts.set(indicator.subjectId, (counts.get(indicator.subjectId) || 0) + 1)
  }

  // Subjects in the bundle that never passed the source cross-check. Eight of
  // the served subject-grades are in this state (see docs/TODO.md P1-1); the
  // app says so rather than presenting them as equal to the rest.
  const unverified = subjects.filter((s) => s.verified === false)

  return (
    <div>
      <Link
        to="/portal/curriculum"
        className="mb-6 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
      >
        ← All grades
      </Link>

        <header className="mb-8">
          <p className="section-heading">{gradeBand(grade)}</p>
          <h1 className="page-title mt-1">{gradeLabel(grade)}</h1>
          <p className="page-subtitle">
            {subjects.length
              ? `${subjects.length} subject${subjects.length === 1 ? '' : 's'} · ${indicators.length} indicators`
              : 'Pick a subject to browse its strands, sub-strands and indicators.'}
          </p>
          {unverified.length > 0 && (
            <p className="mt-2 text-xs text-amber-700">
              {unverified.length === 1 ? 'One subject here has' : `${unverified.length} subjects here have`} not
              been cross-checked against the official NaCCA PDF yet, so treat the wording of
              {unverified.length === 1 ? ' its' : ' their'} indicators as provisional.
            </p>
          )}
        </header>

      {loading && <SkeletonGrid items={6} />}

      {!loading && error && (
        <EmptyState
          title="Curriculum data unavailable"
          message="This grade's curriculum files could not be loaded. Check your connection and reload."
        />
      )}

      {!loading && !error && subjects.length === 0 && (
        <EmptyState
          title={`No subjects for ${gradeLabel(grade)} yet`}
          message="This grade has no extracted subjects in the curriculum bundle."
        />
      )}

      {!loading && !error && subjects.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {subjects.map((subject) => {
            const indicatorCount = counts.get(subject.id) ?? subject.counts?.indicators
            return (
              <Link
                key={subject.id}
                to={`/portal/curriculum/${grade}/${subject.id}`}
                className="card card-hover flex items-start gap-3 p-5"
              >
                <SubjectIcon subjectId={subject.id} name={subject.name} />
                <span className="min-w-0">
                  <span className="block card-title">{subject.name}</span>
                  <span className="card-meta mt-1 block">
                    {indicatorCount != null ? `${indicatorCount} indicators` : 'Browse indicators'}
                  </span>
                  {subject.counts?.strands != null && (
                    <span className="card-meta mt-0.5 block">{subject.counts.strands} strands</span>
                  )}
                    {!subject.hasSchedule && <span className="card-meta mt-1 block">No schedule</span>}
                    {subject.verified === false && (
                      <span className="mt-1 block text-xs text-amber-700">Unverified source</span>
                    )}
                </span>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
