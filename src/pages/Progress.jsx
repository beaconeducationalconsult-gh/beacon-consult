import { useEffect, useState } from 'react'
import { doc, onSnapshot, serverTimestamp, setDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum, useSchedules } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import { GRADES, TERMS, gradeLabel } from '../lib/grades'
import { getAcademicStatus, termWeek } from '../lib/academicCalendar'

/**
 * Per-teacher record of what has actually been taught.
 * Stored as progress/{uid} = { weeks: { "grade|subject": [termWeek…] } } so a
 * single document covers every class — see docs/data-model.md.
 */
export default function Progress() {
  const { user } = useAuth()
  const toast = useToast()
  const [grade, setGrade] = useState('B1')
  const [subjectId, setSubjectId] = useState('')
  const [term, setTerm] = useState(1)
  const [weeks, setWeeks] = useState([])
  const [loading, setLoading] = useState(true)
  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(grade)
  const { lessons } = useSchedules(grade, subjectId)

  const key = `${grade}|${subjectId}|T${term}`
  const status = getAcademicStatus()
  const currentWeek = status.term?.term === Number(term) ? termWeek(status.term) : null

  useEffect(() => {
    if (!user) return undefined
    return onSnapshot(
      doc(db, 'progress', user.uid),
      (snap) => {
        const data = snap.exists() ? snap.data() : {}
        setWeeks(data.weeks?.[key] || [])
        setLoading(false)
      },
      (error) => {
        console.warn('[beacon] progress unavailable:', error?.code || error)
        setWeeks([])
        setLoading(false)
      }
    )
  }, [user, key])

  const toggleWeek = async (week) => {
    const next = weeks.includes(week) ? weeks.filter((w) => w !== week) : [...weeks, week].sort((a, b) => a - b)
    setWeeks(next)
    try {
      await setDoc(doc(db, 'progress', user.uid), { weeks: { [key]: next }, updatedAt: serverTimestamp() }, { merge: true })
    } catch (error) {
      toast.error(`Could not save your progress: ${error?.code || error.message}`)
    }
  }

  const completion = Math.min(100, Math.round((weeks.length / 12) * 100))
  const scheduledWeeks = [...new Set((lessons || []).filter((l) => (l.subjectId === subjectId || l.subject === subjectId) && Number(l.term) === Number(term)).map((l) => Number(l.week)))]

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Curriculum progress</h1>
        <p className="page-subtitle">Tick off each week you have taught — it stays with your account, and works offline.</p>
      </header>

      <div className="card mb-6 grid gap-4 p-5 sm:grid-cols-3">
        <div>
          <label className="label-caps" htmlFor="p-grade">Grade</label>
          <select id="p-grade" className="input" value={grade} onChange={(e) => { setGrade(e.target.value); setSubjectId('') }}>
            {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
          </select>
        </div>
        <div>
          <label className="label-caps" htmlFor="p-subject">Subject</label>
          <SubjectSelect
            id="p-subject"
            className="input"
            grade={grade}
            subjects={subjects}
            loading={loadingSubjects}
            error={subjectsError}
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
          />
        </div>
        <div>
          <label className="label-caps" htmlFor="p-term">Term</label>
          <select id="p-term" className="input" value={term} onChange={(e) => setTerm(e.target.value)}>
            {TERMS.map((t) => <option key={t} value={t}>Term {t}</option>)}
          </select>
        </div>
      </div>

      {!subjectId ? (
        <p className="card p-6 text-sm text-slate-500">Choose a subject to start ticking off weeks.</p>
      ) : loading ? (
        <div className="card h-40 animate-pulse" />
      ) : (
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <p className="section-heading">Weeks taught</p>
            <p className="text-sm font-semibold text-slate-700">{weeks.length}{scheduledWeeks.length ? ` / ${scheduledWeeks.length} scheduled` : ' weeks'}</p>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${completion}%` }} />
          </div>

          <div className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-6">
            {Array.from({ length: 12 }, (_, i) => i + 1).map((week) => {
              const done = weeks.includes(week)
              const scheduled = scheduledWeeks.includes(week)
              return (
                <button
                  key={week}
                  type="button"
                  aria-pressed={done}
                  onClick={() => toggleWeek(week)}
                  className={`rounded-lg border px-2 py-3 text-sm font-semibold transition-colors ${
                    done ? 'border-brand-600 bg-brand-600 text-white' : scheduled ? 'border-brand-200 bg-white text-slate-600' : 'border-slate-200 bg-slate-50 text-slate-400'
                  }`}
                >
                  Wk {week}
                  {currentWeek === week && <span className="mt-1 block text-[10px] font-normal opacity-80">this week</span>}
                </button>
              )
            })}
          </div>

          <p className="card-meta mt-4">
            {scheduledWeeks.length === 0
              ? 'No schedule published for this subject and term — tick weeks as you teach them.'
              : 'Highlighted weeks have scheduled lessons from the curriculum.'}
          </p>
        </div>
      )}
    </div>
  )
}
