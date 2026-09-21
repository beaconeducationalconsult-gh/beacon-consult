import { Link } from 'react-router-dom'
import { TERMS, fmtDate, getAcademicStatus } from '../lib/academicCalendar'

const FEATURES = [
  { title: 'Curriculum browser', body: 'Every NaCCA indicator from KG1 to Basic 9, arranged by strand, sub-strand and content standard.' },
  { title: 'Schemes of learning', body: 'Build a term scheme in minutes, pre-filled from the curriculum schedule for your grade.' },
  { title: 'Lesson plans', body: 'Indicator-linked plans with starter, main activities, plenary and assessment — export to Word or PDF.' },
  { title: 'Question bank', body: 'Author MCQ, short-answer and essay questions once; reuse them in exam papers and quizzes.' },
  { title: 'Study notes & articles', body: 'Share what works in your classroom with teachers across the network.' },
  { title: 'Works offline', body: 'Install it on your phone. Curriculum and your work stay available without a network.' },
]

export default function Landing() {
  const status = getAcademicStatus()

  return (
    <div>
      <main>
        <section className="mx-auto max-w-6xl px-4 pb-16 pt-14 sm:pt-20">
          <p className="section-heading">Ghana · NaCCA standards-based curriculum</p>
          <h1 className="mt-3 max-w-3xl font-display text-4xl font-bold leading-tight text-heading sm:text-5xl">
            Plan your term in an afternoon, not a weekend.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-muted">
            Beacon gives teachers in Ghanaian basic schools the whole curriculum in one place —
            schemes, lesson plans and a shared question bank, mapped to the indicators you
            actually teach.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary px-6 py-3 text-base">
              Request access
            </Link>
            <Link to="/login" className="btn-secondary px-6 py-3 text-base">
              Sign in
            </Link>
            <Link to="/vacancies" className="btn-ghost px-6 py-3 text-base">
              Teaching vacancies →
            </Link>
          </div>

          {status.state === 'in-term' && (
            <p className="mt-6 text-sm text-muted">
              <span className="font-semibold text-accent-600">{status.term.label}</span> is in progress —
              started {fmtDate(status.term.start)}, with {status.daysRemaining} days to go.
            </p>
          )}
        </section>

        <section className="border-y border-line bg-surface">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-14 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="card card-hover p-6">
                <h2 className="card-title">{feature.title}</h2>
                <p className="mt-2 text-sm text-muted">{feature.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-14">
          <h2 className="font-display text-2xl font-bold text-heading">The school year at a glance</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {TERMS.map((term) => (
              <div key={term.term} className="card p-5">
                <p className="section-heading">{term.label}</p>
                <p className="mt-2 font-semibold text-heading">
                  {fmtDate(term.start)} — {fmtDate(term.end)}
                </p>
                <p className="card-meta mt-2">{term.weeks} weeks</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
