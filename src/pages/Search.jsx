import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { collection, getDocs, limit, query, where } from 'firebase/firestore'
import { db } from '../firebase'
import { useCurriculum } from '../hooks/useCurriculum'
import { useAuth } from '../context/AuthContext'
import { GRADES, gradeLabel } from '../lib/grades'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'

/*
 * What Search reads, and how.
 *
 * `notes`, `lesson_plans` and `weekly_forecasts` gate reads on the document
 * (`visibility`), so their list queries must be filtered or Firestore denies
 * them for every ordinary member — see firestore.rules. Search therefore asks
 * for the *shared* slice of those three, plus the author's own private ones, and
 * does not offer drafts written by other people (they are not readable, by
 * design). The rest still take one unfiltered query.
 */
const SOURCES = [
  { name: 'lesson_plans', scoped: true },
  { name: 'notes', scoped: true },
  { name: 'weekly_forecasts', scoped: true },
  { name: 'questions' },
  { name: 'articles' },
  { name: 'vacancies' },
]

const SHARED = [['visibility', 'in', ['members', 'public']]]

/** Every query a source needs, each one provable against its read rule. */
function queriesFor(source, uid) {
  const ref = () => collection(db, source.name)
  const clause = (c) => query(ref(), ...c, limit(100))
  if (!source.scoped) return [clause([])]
  const mine = uid ? [clause([where('authorId', '==', uid)])] : []
  return [...mine, clause(SHARED.map(([field, op, value]) => where(field, op, value)))]
}

/** One search box across curriculum indicators and the shared libraries. */
export default function Search() {
  const [searchParams] = useSearchParams()
  const q = searchParams.get('q')
  const [term, setTerm] = useState(q || '')
  const [syncedQ, setSyncedQ] = useState(q)
  const [grade, setGrade] = useState('B1')
  const [rows, setRows] = useState(null)
  const { user } = useAuth()
  const uid = user?.uid
  const { indicators, grade: loadedGrade, error: curriculumError } = useCurriculum(grade)

  // Adopt a new ?q= when the top-bar search navigates here. Render-phase state
  // adjustment (per React docs) — an effect would cascade an extra render.
  if (q !== syncedQ) {
    setSyncedQ(q)
    if (q != null) setTerm(q)
  }

  const needle = term.trim().toLowerCase()

  const curriculumHits = useMemo(() => {
    if (needle.length < 2) return []
    return indicators
      .filter((i) =>
        String(i.code).toLowerCase().includes(needle) ||
        String(i.description || '').toLowerCase().includes(needle) ||
        String(i.strandName || '').toLowerCase().includes(needle)
      )
      .slice(0, 25)
  }, [indicators, needle])

  useEffect(() => {
    // Below two characters we simply do not fetch; the render guard below hides
    // any previous results, so no state has to be written here.
    if (needle.length < 2) return undefined
    let active = true
    Promise.all(
      SOURCES.flatMap((source) => queriesFor(source, uid).map((q, i) =>
        getDocs(q).then((snap) => snap.docs
          .filter((d, index, all) => all.findIndex((other) => other.id === d.id) === index)
          .map((d) => ({ id: d.id, _collection: source.name, _scoped: source.scoped, _q: i, ...d.data() })))
      ))
    )
      .then((groups) => {
        if (!active) return
        const matches = groups
          .flat()
          .filter((row, index, all) => all.findIndex((other) => other._collection === row._collection && other.id === row.id) === index)
          .filter((row) =>
            [row.title, row.prompt, row.question, row.content, row.summary, row.subjectName, row.role, row.description]
              .filter(Boolean)
              .some((field) => String(field).toLowerCase().includes(needle))
          )
          .slice(0, 40)
        setRows(matches)
      })
      .catch(() => active && setRows([]))
    return () => {
      active = false
    }
  }, [needle, uid])

  const linkFor = (row) => {
    switch (row._collection) {
      case 'lesson_plans': return `/portal/plans/${row.id}`
      case 'weekly_forecasts': return `/portal/forecasts/${row.id}`
      case 'notes': return `/portal/notes/${row.id}`
      case 'articles': return `/portal/articles/${row.id}`
      case 'questions': return '/portal/questions'
      case 'vacancies': return '/portal/vacancies'
      default: return '/portal'
    }
  }

  const labelFor = (row) => {
    const labels = {
      lesson_plans: 'Lesson plan',
      weekly_forecasts: 'Scheme',
      notes: 'Note',
      articles: 'Article',
      questions: 'Question',
      vacancies: 'Vacancy',
    }
    return labels[row._collection] || row._collection
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Search</h1>
        <p className="page-subtitle">Search curriculum indicators and everything members have shared.</p>
      </header>

      <div className="card flex flex-wrap gap-3 p-5">
        <input
          type="search"
          autoFocus
          className="input min-w-56 flex-1"
          placeholder="Search indicators, plans, questions, notes…"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <select className="input max-w-44" value={grade} onChange={(e) => setGrade(e.target.value)} aria-label="Curriculum grade">
          {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
        </select>
      </div>

      {needle.length < 2 && (
        <p className="mt-6 text-sm text-muted">Type at least two characters to search.</p>
      )}

      {needle.length >= 2 && (
        <div className="mt-6 space-y-8">
          <section>
            <h2 className="section-heading mb-3">Curriculum · {gradeLabel(loadedGrade)}</h2>
            {curriculumError ? (
              <p className="card p-5 text-sm text-danger-600 dark:text-danger-500">
                The {gradeLabel(loadedGrade)} curriculum could not be loaded ({curriculumError.code || 'error'}), so
                curriculum matches are missing from these results.
              </p>
            ) : curriculumHits.length === 0 ? (
              <p className="card p-5 text-sm text-muted">No indicators match in this grade. Try another grade.</p>
            ) : (
              <ul className="space-y-2">
                {curriculumHits.map((indicator) => (
                  <li key={indicator.id || indicator.code} className="card p-4">
                    <p className="font-mono text-xs font-semibold text-brand-700 dark:text-brand-300">{indicator.code}</p>
                    <p className="mt-1 text-sm text-text">{indicator.description}</p>
                    <p className="card-meta mt-1">{indicator.strandName} · {indicator.subStrandName}</p>
                    <Link to={`/portal/plans/new?indicator=${encodeURIComponent(indicator.code)}&grade=${loadedGrade}`} className="link mt-2 inline-block text-xs">
                      Plan a lesson →
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="section-heading mb-3">Shared by members</h2>
            {rows === null && <SkeletonList rows={3} />}
            {rows?.length === 0 && (
              <EmptyState title="Nothing found" message="Try a different word, or check the grade selector for curriculum results." />
            )}
            <ul className="space-y-2">
              {rows?.map((row) => (
                <li key={`${row._collection}-${row.id}`} className="card p-4">
                  <div className="flex items-center gap-2">
                    <span className="chip">{labelFor(row)}</span>
                    {row.authorName && <span className="card-meta">{row.authorName}</span>}
                  </div>
                  <Link to={linkFor(row)} className="mt-2 block text-sm font-medium text-heading hover:underline">
                    {row.title || row.prompt || row.question || row.role || row.subjectName || 'Untitled'}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  )
}
