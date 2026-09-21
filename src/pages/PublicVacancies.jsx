import { useEffect, useState } from 'react'
import { collection, getDocs, query, where } from 'firebase/firestore'
import { db } from '../firebase'
import Navbar from '../components/Navbar'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { fmtDate, daysUntil } from '../lib/academicCalendar'

/** Public: `vacancies` where status == 'published' is readable without auth. */
export default function PublicVacancies() {
  const [state, setState] = useState({ loading: true, vacancies: [], error: null })

  useEffect(() => {
    let active = true
    getDocs(query(collection(db, 'vacancies'), where('status', '==', 'published')))
      .then((snap) => {
        if (!active) return
        const vacancies = snap.docs
          .map((d) => ({ id: d.id, ...d.data() }))
          .sort((a, b) => String(a.deadline || '').localeCompare(String(b.deadline || '')))
        setState({ loading: false, vacancies, error: null })
      })
      .catch((error) => active && setState({ loading: false, vacancies: [], error }))
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="page-title">Teaching vacancies</h1>
        <p className="page-subtitle">Openings posted by schools in the Beacon network.</p>

        <div className="mt-8 space-y-4">
          {state.loading && <SkeletonList rows={3} />}
          {!state.loading && state.error && (
            <EmptyState title="Vacancies are unavailable" message="Please try again in a moment." />
          )}
          {!state.loading && !state.error && state.vacancies.length === 0 && (
            <EmptyState title="No vacancies posted yet" message="New openings appear here as schools publish them." />
          )}
          {state.vacancies.map((vacancy) => {
            const closing = vacancy.deadline ? daysUntil(vacancy.deadline) : null
            return (
              <article key={vacancy.id} className="card card-hover p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="card-title text-lg">{vacancy.role || 'Teaching vacancy'}</h2>
                    <p className="card-meta mt-1">{vacancy.school || vacancy.schoolName}</p>
                  </div>
                  {closing != null && (
                    <span className={`chip ${closing < 0 ? 'bg-slate-100 text-slate-500' : closing <= 7 ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
                      {closing < 0 ? 'Closed' : closing === 0 ? 'Closes today' : `${closing} days left`}
                    </span>
                  )}
                </div>
                {vacancy.description && <p className="mt-4 text-sm text-slate-600">{vacancy.description}</p>}
                <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
                  {vacancy.grade && <div><dt className="inline font-semibold">Grade: </dt><dd className="inline">{vacancy.grade}</dd></div>}
                  {vacancy.subject && <div><dt className="inline font-semibold">Subject: </dt><dd className="inline">{vacancy.subject}</dd></div>}
                  {vacancy.deadline && <div><dt className="inline font-semibold">Deadline: </dt><dd className="inline">{fmtDate(vacancy.deadline)}</dd></div>}
                </dl>
                {vacancy.contact && (
                  <p className="mt-4 text-sm">
                    <span className="font-semibold text-slate-700">How to apply: </span>
                    <span className="text-slate-600">{vacancy.contact}</span>
                  </p>
                )}
              </article>
            )
          })}
        </div>
      </main>
    </div>
  )
}
