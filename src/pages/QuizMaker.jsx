import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCollection } from '../hooks/useCollection'
import { useToast } from '../context/ToastContext'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import { downloadQuizPptx } from '../lib/quizPptx'
import { downloadQuestionPaper } from '../lib/questionPaper'
import { gradeLabel } from '../lib/grades'

/** Turn bank questions into a classroom quiz slideshow (PPTX) or a paper. */
export default function QuizMaker() {
  const toast = useToast()
  const [selected, setSelected] = useState([])
  const [title, setTitle] = useState('Class quiz')
  const [busy, setBusy] = useState(false)
  const { rows, loading, error } = useCollection('questions', { max: 200 })

  const chosen = useMemo(() => rows.filter((q) => selected.includes(q.id)), [rows, selected])
  const totalMarks = chosen.reduce((sum, q) => sum + (Number(q.marks) || 1), 0)

  const toggle = (id) => setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]))
  const selectAll = () => setSelected(rows.map((q) => q.id))

  const buildPptx = async () => {
    if (!chosen.length) return toast.error('Select at least one question.')
    setBusy(true)
    try {
      const first = chosen[0]
      await downloadQuizPptx(chosen, {
        title,
        subjectName: first.subjectName || first.subjectId,
        grade: first.grade,
        term: first.term || 1,
      })
      toast.success('Quiz slideshow downloaded')
    } catch (error) {
      toast.error(`Could not build the slideshow: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const buildPaper = () => {
    if (!chosen.length) return toast.error('Select at least one question.')
    const first = chosen[0]
    downloadQuestionPaper(chosen, {
      subjectName: first.subjectName || first.subjectId,
      grade: first.grade,
      term: first.term || 1,
      totalMarks,
    })
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Quiz maker</h1>
          <p className="page-subtitle">Select questions and export a slideshow for class or a printed paper.</p>
        </div>
        <Link to="/portal/questions" className="btn-secondary">Back to the bank</Link>
      </header>

      <div className="card mb-4 flex flex-wrap items-end justify-between gap-4 p-5">
        <div className="min-w-56 flex-1">
          <label className="label-caps" htmlFor="quiz-title">Quiz title</label>
          <input id="quiz-title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" onClick={selectAll}>Select all ({rows.length})</button>
          <button type="button" className="btn-secondary" onClick={() => setSelected([])}>Clear</button>
          <button type="button" className="btn-accent" onClick={buildPptx} disabled={busy}>
            {busy ? 'Building…' : 'Quiz slides (.pptx)'}
          </button>
          <button type="button" className="btn-primary" onClick={buildPaper}>Exam paper (.pdf)</button>
        </div>
        <p className="w-full text-sm text-slate-600 sm:w-auto">
          <span className="font-semibold">{chosen.length}</span> selected · {totalMarks} marks
        </p>
      </div>

      {error && <DataError what="questions" error={error} />}
{loading && <SkeletonList rows={4} />}
      {!loading && !error && rows.length === 0 && (
        <EmptyState
          title="The bank is empty"
          message="Add questions first, then come back to build a quiz."
          action={<Link to="/portal/questions/new" className="btn-primary mt-2">Add a question</Link>}
        />
      )}

      <ul className="space-y-2">
        {rows.map((question) => (
          <li key={question.id} className="card flex items-start gap-3 p-4">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600"
              checked={selected.includes(question.id)}
              onChange={() => toggle(question.id)}
              aria-label="Include in quiz"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-800">{question.prompt || question.question}</p>
              <p className="card-meta mt-1">
                {question.subjectName || question.subjectId} · {gradeLabel(question.grade)} · {question.marks || 1} mark(s)
                {question.answer ? ' · has answer' : ''}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
