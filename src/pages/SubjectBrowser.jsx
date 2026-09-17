import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { buildTree, isPlaceholder, useCurriculum } from '../hooks/useCurriculum'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import SubjectIcon from '../components/SubjectIcon'
import { subjectTheme } from '../lib/subjectThemes'
import { gradeLabel } from '../lib/grades'

/** Strand → sub-strand → content standard → indicators. Static JSON only. */
export default function SubjectBrowser() {
  const { subjectId } = useParams()
  const [grade, setGrade] = useState('B1')
  const { loading, subjects, indicators, error } = useCurriculum(grade)
  const [openSub, setOpenSub] = useState(null)

  const subject = subjects.find((s) => s.id === subjectId)
  const tree = useMemo(
    () => (loading ? [] : buildTree(indicators, subjectId)),
    [loading, indicators, subjectId]
  )

  const totalIndicators = tree.reduce(
    (sum, strand) => sum + strand.subStrands.reduce((s, sub) => s + sub.standards.reduce((n, std) => n + std.indicators.length, 0), 0),
    0
  )

  return (
    <div>
      <Link to="/portal/curriculum" className="mb-6 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        ← All grades
      </Link>

      <header className="mb-8 flex flex-wrap items-start gap-4">
        <SubjectIcon subjectId={subjectId} name={subject?.name} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="page-title">{subject?.name || subjectId}</h1>
          <p className="page-subtitle">
            {gradeLabel(grade)} {totalIndicators ? `· ${totalIndicators} indicators` : ''}
          </p>
          {subject?.strandNames?.length ? (
            <p className="card-meta mt-1">Strands: {subject.strandNames.join(' · ')}</p>
          ) : null}
        </div>
        <div>
          <label className="label-caps" htmlFor="grade-switch">Grade</label>
          <select id="grade-switch" className="input" value={grade} onChange={(e) => { setGrade(e.target.value); setOpenSub(null) }}>
            {['KG1', 'KG2', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9'].map((g) => (
              <option key={g} value={g}>{gradeLabel(g)}</option>
            ))}
          </select>
        </div>
      </header>

      {loading && <SkeletonList rows={4} />}
      {!loading && error && <EmptyState title="Could not load this grade" message="It may not have extracted curriculum data yet." />}
      {!loading && !error && tree.length === 0 && (
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
