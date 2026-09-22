import { Link } from 'react-router-dom'
import { useGrades } from '../hooks/useCurriculum'
import { SkeletonGrid } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { PageHeader } from '../ui'
import { gradeLabel, gradeBand } from '../lib/grades'

/** Grade grid. Pure static reads — works offline, no Firestore. */
export default function Curriculum() {
  const { loading, grades, error } = useGrades()

  return (
    <div>
      <PageHeader
        title="Curriculum"
        subtitle="The NaCCA standards-based curriculum, KG1 to Basic 9. Pick a grade to browse its subjects and indicators."
      />

      {loading && <SkeletonGrid items={6} />}
      {!loading && error && (
        <EmptyState title="Curriculum data unavailable" message="The bundle could not be loaded. Check your connection and reload." />
      )}

      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {grades.map((grade) => {
            const id = grade.id || grade
            const subjects = grade.subjects ?? grade.subjectCount
            const indicators = grade.indicators
            return (
              <Link key={id} to={`/portal/curriculum/${id}`} className="card card-hover p-5">
                <p className="section-heading">{gradeBand(id)}</p>
                <h2 className="mt-1 card-title text-lg">{gradeLabel(id)}</h2>
                <p className="card-meta mt-3">
                  {subjects != null ? `${subjects} subject${subjects === 1 ? '' : 's'}` : 'Browse subjects'}
                  {indicators != null && ` · ${indicators} indicators`}
                </p>
                {grade.hasSchedules?.length ? (
                  <p className="mt-2"><span className="chip-brand">{grade.hasSchedules.length} scheduled</span></p>
                ) : null}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
