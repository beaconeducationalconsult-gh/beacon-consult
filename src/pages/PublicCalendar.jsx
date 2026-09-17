import Navbar from '../components/Navbar'
import { ACADEMIC_YEAR, TERMS, fmtDate, getAcademicStatus, termProgress } from '../lib/academicCalendar'

/** Public: the Ghana academic calendar. Static and pure — works offline. */
export default function PublicCalendar() {
  const status = getAcademicStatus()

  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="page-title">Academic calendar</h1>
        <p className="page-subtitle">{ACADEMIC_YEAR} school year · Ghana basic education</p>

        {status.state === 'in-term' && (
          <div className="card mt-8 border-l-4 border-l-emerald-500 p-6">
            <p className="section-heading">Currently in session</p>
            <p className="mt-1 font-semibold text-slate-800">
              {status.term.label} — {status.daysRemaining} days remaining
            </p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.round(termProgress(status.term) * 100)}%` }} />
            </div>
          </div>
        )}

        <ol className="mt-6 space-y-4">
          {TERMS.map((term) => {
            const progress = termProgress(term)
            return (
              <li key={term.term} className="card p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="card-title text-lg">{term.label}</h2>
                  <span className="chip">{term.weeks} weeks</span>
                </div>
                <p className="mt-2 text-sm text-slate-700">
                  {fmtDate(term.start)} — {fmtDate(term.end)}
                </p>
                <p className="card-meta mt-1">{term.note}</p>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.round(progress * 100)}%` }} />
                </div>
              </li>
            )
          })}
        </ol>
      </main>
    </div>
  )
}
