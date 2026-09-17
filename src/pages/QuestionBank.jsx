import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteDoc, doc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import NotesTabs from '../components/NotesTabs'
import { GRADES, gradeLabel } from '../lib/grades'
import { isoWeekKey } from '../lib/week'
import { downloadQuestionPaper } from '../lib/questionPaper'

const TYPE_LABELS = { mcq: 'Multiple choice', short: 'Short answer', essay: 'Essay', truefalse: 'True / false' }

export default function QuestionBank() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('all')
  const [grade, setGrade] = useState('')
  const [type, setType] = useState('')
  const [selected, setSelected] = useState([])
  const [pendingDelete, setPendingDelete] = useState(null)
  const { rows, loading } = useCollection('questions', { max: 200 })

  const visible = useMemo(
    () =>
      rows
        .filter((q) => (scope === 'mine' ? q.authorId === user.uid : scope === 'week' ? q.weekKey === isoWeekKey() : true))
        .filter((q) => !grade || q.grade === grade)
        .filter((q) => !type || q.type === type),
    [rows, scope, user.uid, grade, type]
  )

  const toggle = (question) =>
    setSelected((current) =>
      current.includes(question.id) ? current.filter((id) => id !== question.id) : [...current, question.id]
    )

  const selectedQuestions = rows.filter((q) => selected.includes(q.id))
  const totalMarks = selectedQuestions.reduce((sum, q) => sum + (Number(q.marks) || 1), 0)

  const exportPaper = () => {
    if (!selectedQuestions.length) return toast.error('Select some questions first.')
    const first = selectedQuestions[0]
    downloadQuestionPaper(selectedQuestions, {
      subjectName: first.subjectName || first.subjectId,
      grade: first.grade,
      term: first.term || 1,
      totalMarks,
    })
  }

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'questions', pendingDelete.id))
      toast.success('Question deleted')
    } catch (error) {
      toast.error(`Could not delete: ${error?.code || error.message}`)
    } finally {
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Question bank</h1>
          <p className="page-subtitle">Author questions once, then build exam papers and slideshows from them.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/portal/questions/generate" className="btn-secondary">Generate</Link>
          <Link to="/portal/questions/quiz" className="btn-secondary">Quiz slides</Link>
          <Link to="/portal/questions/new" className="btn-primary">New question</Link>
        </div>
      </header>

      <NotesTabs
        tabs={[
          { value: 'all', label: 'All', count: rows.length },
          { value: 'mine', label: 'Mine', count: rows.filter((q) => q.authorId === user.uid).length },
          { value: 'week', label: 'This week', count: rows.filter((q) => q.weekKey === isoWeekKey()).length },
        ]}
        active={scope}
        onChange={setScope}
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <select className="input max-w-44" value={grade} onChange={(e) => setGrade(e.target.value)} aria-label="Filter by grade">
          <option value="">All grades</option>
          {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
        </select>
        <select className="input max-w-52" value={type} onChange={(e) => setType(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>

      {selected.length > 0 && (
        <div className="card mb-4 flex flex-wrap items-center justify-between gap-3 border-brand-200 bg-brand-50 p-4">
          <p className="text-sm text-brand-800">
            <span className="font-semibold">{selected.length}</span> selected · {totalMarks} marks
          </p>
          <div className="flex gap-2">
            <button type="button" className="btn-secondary" onClick={() => setSelected([])}>Clear</button>
            <button type="button" className="btn-accent" onClick={exportPaper}>Export exam paper (PDF)</button>
          </div>
        </div>
      )}

      {loading && <SkeletonList rows={4} />}
      {!loading && visible.length === 0 && (
        <EmptyState
          title="No questions here yet"
          message="Add questions by hand, or generate them from an indicator and edit before saving."
          action={<Link to="/portal/questions/new" className="btn-primary mt-2">Add a question</Link>}
        />
      )}

      <ul className="space-y-3">
        {visible.map((question) => (
          <li key={question.id} className="card p-5">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
                checked={selected.includes(question.id)}
                onChange={() => toggle(question)}
                aria-label="Select question for the exam paper"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="chip">{TYPE_LABELS[question.type] || question.type}</span>
                  <span className="chip-brand">{gradeLabel(question.grade)}</span>
                  <span className="card-meta">{question.subjectName || question.subjectId}</span>
                  <span className="card-meta">{question.marks || 1} mark(s)</span>
                  {question.weekKey && <span className="card-meta">week {question.weekKey}</span>}
                </div>
                <p className="mt-2 text-sm text-slate-800">{question.prompt || question.question}</p>
                {question.options?.length > 0 && (
                  <ol className="mt-2 space-y-1 text-sm text-slate-600">
                    {question.options.map((option, index) => (
                      <li key={index}>{String.fromCharCode(65 + index)}. {option}</li>
                    ))}
                  </ol>
                )}
                {question.answer && (
                  <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                    <span className="font-semibold">Answer: </span>{question.answer}
                  </p>
                )}
                <div className="mt-3 flex items-center gap-3">
                  <span className="card-meta">{question.authorName}</span>
                  {(question.authorId === user.uid || isAdmin) && (
                    <>
                      <Link to={`/portal/questions/${question.id}/edit`} className="text-xs font-semibold text-brand-700 hover:underline">Edit</Link>
                      <button type="button" className="text-xs font-semibold text-red-600 hover:underline" onClick={() => setPendingDelete(question)}>Delete</button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <ConfirmModal open={Boolean(pendingDelete)} title="Delete this question?" confirmLabel="Delete" onConfirm={remove} onCancel={() => setPendingDelete(null)} />
    </div>
  )
}
