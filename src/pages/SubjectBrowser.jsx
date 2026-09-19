import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { buildTree, isPlaceholder, useCurriculum } from '../hooks/useCurriculum'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import SubjectIcon from '../components/SubjectIcon'
import { subjectTheme } from '../lib/subjectThemes'
import { GRADES, gradeLabel } from '../lib/grades'
import { packFiles, warmPack } from '../lib/offlinePack'
import { modelsFor } from '../lib/teachingModels'

/**
 * Strand → sub-strand → content standard → indicators. Static JSON only.
 *
 * Both ids come from the URL — `/portal/curriculum/B4/mathematics`. The grade
 * used to be a hard-coded `useState('B1')` while the route param was read as a
 * subject id, so every link from the grade grid resolved against the wrong
 * grade and matched no indicators.
 */
export default function SubjectBrowser() {
  const { gradeId, subjectId } = useParams()
  const navigate = useNavigate()
  const grade = String(gradeId || '').toUpperCase()
  const { loading, subjects, indicators, error } = useCurriculum(grade)
  const [openSub, setOpenSub] = useState(null)
  /*
   * Offline pack (P3-2): which files have come down for this subject-grade.
   *
   * The state carries the key it belongs to, so switching subject (or grade)
   * shows the idle button again without an effect writing state on mount — the
   * stale key simply does not match this page.
   */
  const packKey = `${grade}|${subjectId}`
  const [pack, setPack] = useState({ key: null, state: 'idle', done: 0, total: 1, result: null, label: '' })
  const idle = { state: 'idle', done: 0, total: 1, result: null, label: '' }
  const current = pack.key === packKey ? pack : idle

  const saveOffline = async () => {
    const files = packFiles(grade, subjectId)
    const update = (changes) => setPack((previous) => ({ key: packKey, ...(previous.key === packKey ? previous : idle), ...changes }))
    update({ state: 'saving', done: 0, total: files.length, result: null, label: files[0].label })
    const result = await warmPack(files, {
      onProgress: ({ file, done }) => update({ state: 'saving', done, label: file.label }),
    })
    update({ state: 'done', done: files.length, total: files.length, result, label: '' })
  }

  const subject = subjects.find((s) => s.id === subjectId)
  const tree = useMemo(
    () => (loading ? [] : buildTree(indicators, subjectId)),
    [loading, indicators, subjectId]
  )

  const totalIndicators = tree.reduce(
    (sum, strand) => sum + strand.subStrands.reduce((s, sub) => s + sub.standards.reduce((n, std) => n + std.indicators.length, 0), 0),
    0
  )

  // A subject id that is not in this grade: say so, and offer the way back.
  const unknownSubject = !loading && !error && subjects.length > 0 && !subject

  return (
    <div>
      <nav className="mb-6 flex flex-wrap items-center gap-1 text-sm text-slate-500">
        <Link to="/portal/curriculum" className="hover:text-slate-800">All grades</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/portal/curriculum/${grade}`} className="hover:text-slate-800">{gradeLabel(grade)}</Link>
        <span aria-hidden="true">/</span>
        <span className="text-slate-800">{subject?.name || subjectId}</span>
      </nav>

      <header className="mb-8 flex flex-wrap items-start gap-4">
        <SubjectIcon subjectId={subjectId} name={subject?.name} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="page-title">{subject?.name || subjectId}</h1>
          <p className="page-subtitle">
            {gradeLabel(grade)} {totalIndicators ? `· ${totalIndicators} indicators · ${tree.length} strands` : ''}
          </p>
        </div>
        <div className="flex flex-col items-stretch gap-2 sm:items-end">
          {/* Teaching models (P3-4) exist for one subject-grade so far; the link
              only appears where there is something to open. */}
          {modelsFor(subjectId, grade).length > 0 && (
            <Link to="/portal/models" className="btn-secondary">Teaching models</Link>
          )}
          <div>
            <label className="label-caps" htmlFor="grade-switch">Grade</label>
            {/* A subject id rarely exists in every grade, so switching grade
                lands on that grade's subject list rather than a dead end. */}
            <select
              id="grade-switch"
              className="input"
              value={GRADES.includes(grade) ? grade : ''}
              onChange={(e) => navigate(`/portal/curriculum/${e.target.value}`)}
            >
              {!GRADES.includes(grade) && <option value="">{gradeLabel(grade)}</option>}
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>

          {/* Offline pack (P3-2). Offline browsing already works for anything
              you have opened; this is for "save it now, before I leave wifi". */}
          <div className="sm:text-right">
            <button
              type="button"
              className="btn-secondary"
              onClick={saveOffline}
              disabled={loading || current.state === 'saving'}
            >
              {current.state === 'saving' ? `Saving ${current.done}/${current.total}…` : 'Save for offline'}
            </button>
            <p className="card-meta mt-1 max-w-56" aria-live="polite">
              {current.state === 'idle' && 'Downloads this subject’s indicators, schemes and lesson schedule.'}
              {current.state === 'saving' && `Fetching ${current.label}…`}
              {current.state === 'done' && current.result?.complete
                && `Saved ${current.result.size} — this subject now opens without a connection.`}
              {current.state === 'done' && !current.result?.complete
                && `Saved ${current.result?.downloaded} of ${current.result?.files} files (${current.result?.missing
                  ?.map((m) => m.label)
                  .join(', ')} unavailable). The rest works offline.`}
            </p>
          </div>
        </div>
      </header>

      {loading && <SkeletonList rows={4} />}
      {!loading && error && (
        <EmptyState title="Could not load this grade" message="The curriculum bundle could not be fetched. Check your connection and reload." />
      )}

      {unknownSubject && (
        <EmptyState
          title={`${subjectId} is not a ${gradeLabel(grade)} subject`}
          message="This grade does not have that subject. Choose one of its subjects instead."
          action={<Link to={`/portal/curriculum/${grade}`} className="btn-secondary mt-1">See {gradeLabel(grade)} subjects</Link>}
        />
      )}

      {!loading && !error && !unknownSubject && tree.length === 0 && (
        <EmptyState
          title={`No indicators for ${subject?.name || subjectId} in ${gradeLabel(grade)}`}
          message="This subject and grade combination has no extracted indicators yet."
        />
      )}

      <div className="space-y-4">
        {tree.map((strand) => (
          <section key={strand.name} className="card overflow-hidden">
            <div className={`border-b border-slate-100 px-5 py-4 ${subjectTheme(subjectId).bg}`}>
              <h2 className={`font-semibold ${subjectTheme(subjectId).text}`}>
                {strand.number ? `${strand.number}. ` : ''}{strand.name}
              </h2>
              <p className="card-meta mt-0.5">{strand.subStrands.length} sub-strand(s)</p>
            </div>

            <ul className="divide-y divide-slate-100">
              {strand.subStrands.map((sub) => {
                const isOpen = openSub === `${strand.name}|${sub.name}`
                const count = sub.standards.reduce((n, std) => n + std.indicators.length, 0)
                return (
                  <li key={sub.name}>
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      onClick={() => setOpenSub(isOpen ? null : `${strand.name}|${sub.name}`)}
                      className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-slate-50"
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-slate-800">{sub.name}</span>
                        <span className="card-meta">{sub.standards.length} content standard(s) · {count} indicator(s)</span>
                      </span>
                      <span className="text-slate-400">{isOpen ? '−' : '+'}</span>
                    </button>

                    {isOpen && (
                      <div className="space-y-4 bg-slate-50/60 px-5 pb-5 pt-2">
                        {sub.standards.map((standard) => (
                          <div key={standard.code}>
                            <p className="text-xs font-semibold text-slate-500">{standard.code}</p>
                            {standard.description && (
                              <p className="mt-0.5 text-sm text-slate-700">{standard.description}</p>
                            )}
                            <ul className="mt-2 space-y-2">
                              {standard.indicators.map((indicator) => (
                                <li key={indicator.id || indicator.code} className="rounded-lg border border-slate-200 bg-white p-3">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="font-mono text-xs font-semibold text-brand-700">{indicator.code}</span>
                                    {isPlaceholder(indicator.description) && <span className="chip bg-amber-50 text-amber-700">placeholder</span>}
                                  </div>
                                  <p className="mt-1 text-sm text-slate-700">{indicator.description}</p>
                                  <Link
                                    to={`/portal/plans/new?indicator=${encodeURIComponent(indicator.code)}&grade=${grade}`}
                                    className="mt-2 inline-block text-xs font-semibold text-brand-700 hover:underline"
                                  >
                                    Plan a lesson on this →
                                  </Link>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
