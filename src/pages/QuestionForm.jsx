import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { addDoc, collection, doc, getDoc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import { GRADES, gradeLabel } from '../lib/grades'
import { isoWeekKey } from '../lib/week'
import IndicatorPicker from '../components/IndicatorPicker'

const TYPES = [
  ['mcq', 'Multiple choice'],
  ['truefalse', 'True / false'],
  ['short', 'Short answer'],
  ['essay', 'Essay'],
]

const empty = {
  type: 'mcq',
  grade: 'B1',
  subjectId: '',
  term: 1,
  prompt: '',
  options: ['', '', '', ''],
  answer: '',
  marks: 1,
  indicatorIds: [],
  explanation: '',
}

export default function QuestionForm() {
  const { questionId } = useParams()
  const editing = Boolean(questionId)
  const { user, profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [showIndicators, setShowIndicators] = useState(false)
  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(form.grade)

  useEffect(() => {
    if (!editing) return
    getDoc(doc(db, 'questions', questionId))
      .then((snap) => {
        if (snap.exists()) setForm({ ...empty, ...snap.data() })
      })
      .finally(() => setLoading(false))
  }, [editing, questionId])

  const setOption = (index, value) =>
    setForm((current) => ({ ...current, options: current.options.map((option, i) => (i === index ? value : option)) }))

  const save = async (event) => {
    event.preventDefault()
    if (!form.prompt.trim()) return toast.error('Write the question first.')
    if (form.type === 'mcq' && form.options.filter((o) => o.trim()).length < 2) return toast.error('A multiple-choice question needs at least two options.')

    setSaving(true)
    const payload = {
      ...form,
      subjectName: subjects.find((s) => s.id === form.subjectId)?.name || form.subjectId,
      marks: Number(form.marks) || 1,
      term: Number(form.term) || 1,
      options: form.type === 'mcq' ? form.options.map((o) => o.trim()).filter(Boolean) : [],
      indicatorCodes: (form.indicatorIds || []).map((i) => i.code),
      weekKey: form.weekKey || isoWeekKey(),
      updatedAt: serverTimestamp(),
    }
    try {
      if (editing) {
        await updateDoc(doc(db, 'questions', questionId), payload)
        toast.success('Question updated')
        navigate('/portal/questions')
      } else {
        await addDoc(collection(db, 'questions'), {
          ...payload,
          authorId: user.uid,
          authorName: profile?.name || 'Member',
          createdAt: serverTimestamp(),
        })
        toast.success('Question added to the bank')
        navigate('/portal/questions')
      }
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="card h-96 animate-pulse" />

  return (
    <form onSubmit={save}>
      <header className="mb-6">
        <h1 className="page-title">{editing ? 'Edit question' : 'New question'}</h1>
        <p className="page-subtitle">Tag questions with an indicator so papers always match what you taught.</p>
      </header>

      <div className="card space-y-5 p-6">
        <div>
          <label className="label-caps">Question type</label>
          <div className="flex flex-wrap gap-2">
            {TYPES.map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={form.type === value}
                onClick={() => setForm({ ...form, type: value })}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${form.type === value ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <label className="label-caps" htmlFor="q-grade">Grade</label>
            <select id="q-grade" className="input" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value, subjectId: '' })}>
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="q-subject">Subject</label>
            <SubjectSelect
              id="q-subject"
              className="input"
              grade={form.grade}
              subjects={subjects}
              loading={loadingSubjects}
              error={subjectsError}
              value={form.subjectId}
              onChange={(e) => setForm({ ...form, subjectId: e.target.value })}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="q-term">Term</label>
            <select id="q-term" className="input" value={form.term} onChange={(e) => setForm({ ...form, term: e.target.value })}>
              {[1, 2, 3].map((t) => <option key={t} value={t}>Term {t}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="q-marks">Marks</label>
            <input id="q-marks" type="number" min="1" max="50" className="input" value={form.marks} onChange={(e) => setForm({ ...form, marks: e.target.value })} />
          </div>
        </div>

        <div>
          <label className="label-caps" htmlFor="prompt">Question</label>
          <textarea id="prompt" rows={3} required className="input" value={form.prompt} onChange={(e) => setForm({ ...form, prompt: e.target.value })} />
        </div>

        {form.type === 'mcq' && (
          <div>
            <label className="label-caps">Options</label>
            <div className="space-y-2">
              {form.options.map((option, index) => (
                <div key={index} className="flex items-center gap-2">
                  <span className="w-4 text-sm font-semibold text-slate-500">{String.fromCharCode(65 + index)}</span>
                  <input className="input" value={option} onChange={(e) => setOption(index, e.target.value)} placeholder={`Option ${String.fromCharCode(65 + index)}`} />
                </div>
              ))}
            </div>
            <button type="button" className="btn-ghost mt-2 text-xs" onClick={() => setForm({ ...form, options: [...form.options, ''] })}>+ Add option</button>
          </div>
        )}

        {form.type === 'truefalse' ? (
          <div>
            <label className="label-caps" htmlFor="tf-answer">Correct answer</label>
            <select id="tf-answer" className="input" value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })}>
              <option value="">Choose…</option>
              <option value="True">True</option>
              <option value="False">False</option>
            </select>
          </div>
        ) : (
          <div>
            <label className="label-caps" htmlFor="answer">Answer / marking notes</label>
            <textarea id="answer" rows={2} className="input" value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })} />
          </div>
        )}

        <div>
          <label className="label-caps" htmlFor="explanation">Explanation for learners (optional)</label>
          <textarea id="explanation" rows={2} className="input" value={form.explanation} onChange={(e) => setForm({ ...form, explanation: e.target.value })} />
        </div>

        <div>
          <button type="button" className="btn-ghost text-xs" onClick={() => setShowIndicators((open) => !open)} aria-expanded={showIndicators}>
            {showIndicators ? 'Hide' : 'Link to curriculum indicators'} {form.indicatorIds?.length ? `(${form.indicatorIds.length})` : ''}
          </button>
          {showIndicators && (
            <div className="mt-3">
              <IndicatorPicker
                grade={form.grade}
                subjectId={form.subjectId}
                selected={form.indicatorIds || []}
                onChange={(indicatorIds) => setForm({ ...form, indicatorIds })}
              />
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex justify-end gap-3">
        <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save question'}</button>
      </div>
    </form>
  )
}
