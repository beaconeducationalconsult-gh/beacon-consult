import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useCurriculum } from '../hooks/useCurriculum'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import DataError from '../components/DataError'
import SubjectIcon from '../components/SubjectIcon'
import { MODEL_COMPONENTS } from '../components/models'
import { GRADES, gradeLabel } from '../lib/grades'
import {
  PILOT, attachIndicators, modelledSubjectGrades, modelsFor,
} from '../lib/teachingModels'

/**
 * The teaching models (P3-4) — the pilot, not a library.
 *
 * Five interactive models for mathematics B4, each one named after the served
 * indicators it teaches: a teacher opens the model, uses it on the board, and
 * can see which indicator it belongs to. Everything runs offline, from the same
 * bundle the rest of the portal uses — no external service, no API key.
 */
export default function Models() {
  const { modelId } = useParams()
  const modelled = modelledSubjectGrades()
  const [pick, setPick] = useState(`${PILOT.subjectId}|${PILOT.grade}`)

  const [subjectId, grade] = pick.split('|')
  const { loading, indicators, subjects, error } = useCurriculum(grade)

  const models = useMemo(
    () => modelsFor(subjectId, grade).map((model) => attachIndicators(model, indicators)),
    [subjectId, grade, indicators]
  )

  const subject = subjects.find((s) => s.id === subjectId)
  const selected = models.find((model) => model.id === modelId) || models[0]
  const SelectedModel = selected ? MODEL_COMPONENTS[selected.component] : null

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Teaching models</h1>
        <p className="page-subtitle">
          Interactive models for one subject-grade — the pilot — each one built around the
          indicators it teaches. They work offline and need nothing but the screen.
        </p>
      </header>

      <div className="card mb-6 flex flex-wrap items-end gap-3 p-4">
        <div>
          <label className="label-caps" htmlFor="model-pair">Subject and grade</label>
          <select
            id="model-pair"
            className="input max-w-72"
            value={pick}
            onChange={(event) => setPick(event.target.value)}
          >
            {modelled.map(({ subjectId: s, grade: g }) => (
              <option key={`${s}|${g}`} value={`${s}|${g}`}>
                {subjects.length && s === subjectId ? subject?.name || s : s} · {gradeLabel(g)}
              </option>
            ))}
          </select>
        </div>
        <p className="card-meta">
          {models.length} model{models.length === 1 ? '' : 's'} for this subject-grade. More subjects
          are added once these have been used in a classroom.
        </p>
      </div>

      {loading && <SkeletonList rows={3} />}
      {error && <DataError what="the curriculum for this grade" error={error} />}

      {!loading && !error && models.length === 0 && (
        <EmptyState
          title="No models for this subject-grade yet"
          message="The pilot covers mathematics B4. Choose it above, or open the curriculum to see what is served."
          action={<Link to="/portal/curriculum" className="btn-secondary mt-2">Browse the curriculum</Link>}
        />
      )}

      {!loading && !error && selected && SelectedModel && (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {models.map((model) => (
              <Link
                key={model.id}
                to={`/portal/models/${model.id}`}
                className={model.id === selected.id ? 'chip-brand' : 'chip bg-surface'}
              >
                {model.title}
              </Link>
            ))}
          </div>

          <section className="card p-5">
            <div className="mb-4 flex flex-wrap items-start gap-3">
              <SubjectIcon subjectId={subjectId} name={subject?.name} />
              <div className="min-w-0 flex-1">
                <h2 className="card-title">{selected.title}</h2>
                <p className="card-meta mt-0.5">{selected.blurb}</p>
              </div>
              <span className="chip-brand">{gradeLabel(grade)}</span>
            </div>

            <SelectedModel />

            <div className="mt-5 border-t border-line-2 pt-4">
              <p className="label-caps mb-2">Indicators this model teaches</p>
              <ul className="space-y-2">
                {selected.indicators.map((indicator) => (
                  <li key={indicator.code} className="text-sm">
                    <span className="font-mono text-xs text-brand-700 dark:text-brand-300">{indicator.code}</span>{' '}
                    <span className="text-text">{indicator.description}</span>
                    {!indicator.served && (
                      <span className="ml-1 text-xs text-warning-700 dark:text-warning-500">
                        (not in the served curriculum — the catalogue needs fixing)
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </>
      )}

      {!loading && !error && selected && !SelectedModel && (
        <EmptyState
          title="That model is not built"
          message={`The catalogue names the component "${selected.component}", which does not exist.`}
        />
      )}

      <p className="card-meta mt-6">
        {GRADES.length} grades are served; the models cover the one in the pilot.{' '}
        <Link to={`/portal/curriculum/${grade}/${subjectId}`} className="link">
          Open {subject?.name || subjectId} in the curriculum
        </Link>
      </p>
    </div>
  )
}
