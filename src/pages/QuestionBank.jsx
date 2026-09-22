import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { collection, deleteDoc, doc, serverTimestamp, writeBatch } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { usePagedCollection } from '../hooks/useCollection'
import LoadMore from '../components/LoadMore'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import NotesTabs from '../components/NotesTabs'
import { GRADES, gradeLabel } from '../lib/grades'
import { isoWeekKey } from '../lib/week'
import { buildQuestionPaper, downloadQuestionPaper } from '../lib/questionPaper'
import SaveToLibrary from '../components/SaveToLibrary'
import { PageHeader } from '../ui'
import { suggestFilename } from '../lib/generatedDocs'
import { loadStarterIndex, loadStarterPack, starterToFirestore } from '../lib/starterBank'

const TYPE_LABELS = { mcq: 'Multiple choice', short: 'Short answer', essay: 'Essay', truefalse: 'True / false' }

export default function QuestionBank() {
  const { user, profile, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('all')
  const [grade, setGrade] = useState('')
  const [type, setType] = useState('')
  const [selected, setSelected] = useState([])
  const [pendingDelete, setPendingDelete] = useState(null)
  // Paged, not capped: 200 was silent truncation, and the scope/grade/type
  // tabs filter what has been loaded, so "Load more" is how older questions
  // are reached. See the note in src/hooks/useCollection.js.
  const {
    rows, loading, error, hasMore, loadingMore, loadMore, moreError,
  } = usePagedCollection('questions', { pageSize: 50 })

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

  /*
   * Starter bank (P1-5). The bundle ships practice questions for the primary
   * mathematics indicators; they are not in Firestore until someone imports
   * them, and importing is a deliberate act — the panel is opened, a
   * subject-grade is chosen, the counts are shown, and only then are documents
   * written. Nothing is fetched until it is opened, so the page is as fast as
   * before for anyone who never touches it.
   */
  const [starter, setStarter] = useState({ open: false, loading: false, index: null, pick: '', pack: null, busy: false })

  const openStarter = async () => {
    setStarter((current) => ({ ...current, open: !current.open }))
    if (starter.index || starter.loading) return
    setStarter((current) => ({ ...current, loading: true }))
    const index = await loadStarterIndex()
    setStarter((current) => ({ ...current, loading: false, index }))
  }

  const chooseStarter = async (value) => {
    const [subjectId, grade] = value.split('|')
    setStarter((current) => ({ ...current, pick: value, pack: null, loading: true }))
    const pack = await loadStarterPack(subjectId, grade)
    setStarter((current) => ({ ...current, loading: false, pack: pack ? { ...pack, subjectId, grade } : null }))
  }

  const importStarter = async () => {
    const pack = starter.pack
    if (!pack?.items?.length) return
    setStarter((current) => ({ ...current, busy: true }))
    try {
      // Batched in 400s: a Firestore batch caps at 500 writes, and the largest
      // pack is well under that, but a future subject should not have to be
      // re-imported by hand because one batch silently overflowed.
      let written = 0
      for (let i = 0; i < pack.items.length; i += 400) {
        const batch = writeBatch(db)
        for (const item of pack.items.slice(i, i + 400)) {
          batch.set(doc(collection(db, 'questions')), {
            ...starterToFirestore(item, {
              subjectId: pack.subjectId,
              subjectName: pack.subjectName || pack.subjectId,
              grade: pack.grade,
              authorId: user.uid,
              authorName: profile?.name,
            }),
            weekKey: isoWeekKey(),
            createdAt: serverTimestamp(),
            updatedAt: serverTimestamp(),
          })
        }
        await batch.commit()
        written += Math.min(400, pack.items.length - i)
      }
      toast.success(`Imported ${written} questions into the bank`)
    } catch (error) {
      toast.error(`Could not import: ${error?.code || error.message}`)
    } finally {
      setStarter((current) => ({ ...current, busy: false }))
    }
  }

  const paperOptions = () => {
    const first = selectedQuestions[0] || {}
    return {
      subjectName: first.subjectName || first.subjectId,
      grade: first.grade,
      term: first.term || 1,
      totalMarks,
    }
  }

  // What the library records beside the file (P3-3).
  const paperMeta = () => {
    const first = selectedQuestions[0] || {}
    return {
      subjectId: first.subjectId, subjectName: first.subjectName || first.subjectId,
      grade: first.grade, term: first.term || 1, questions: selectedQuestions.length,
    }
  }

  const exportPaper = () => {
    if (!selectedQuestions.length) return toast.error('Select some questions first.')
    downloadQuestionPaper(selectedQuestions, paperOptions())
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
      <PageHeader
        title="Question bank"
        subtitle="Author questions once, then build exam papers and slideshows from them."
        actions={
          <>
            <Link to="/portal/questions/generate" className="btn-secondary">Generate</Link>
            <Link to="/portal/questions/quiz" className="btn-secondary">Quiz slides</Link>
            <Link to="/portal/questions/new" className="btn-primary">New question</Link>
          </>
        }
      />

      {/* Starter bank (P1-5) — the bundle's practice questions, imported on demand. */}
      <div className="card mb-4 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="card-title">Starter bank</h2>
            <p className="card-meta mt-0.5">
              Ready-made practice questions that ship with the curriculum, written for primary
              mathematics indicators. Import the ones you want — they land in this bank and can be
              edited, deleted or printed like any other question.
            </p>
          </div>
          <button type="button" className="btn-secondary" onClick={openStarter}>
            {starter.open ? 'Hide' : 'Browse starter questions'}
          </button>
        </div>

        {starter.open && (
          <div className="mt-4 border-t border-line pt-4">
            {starter.loading && <p className="card-meta">Loading…</p>}
            {!starter.loading && starter.index === null && (
              <p className="card-meta">The starter bank could not be loaded. Check your connection and try again.</p>
            )}
            {!starter.loading && starter.index && (
              <>
                <label className="label-caps" htmlFor="starter-pick">Subject and grade</label>
                <select
                  id="starter-pick"
                  className="input max-w-72"
                  value={starter.pick}
                  onChange={(e) => chooseStarter(e.target.value)}
                >
                  <option value="">Choose…</option>
                  {Object.entries(starter.index.subjects).map(([subjectId, grades]) =>
                    Object.entries(grades).map(([grade, counts]) => (
                      <option key={`${subjectId}|${grade}`} value={`${subjectId}|${grade}`}>
                        {subjectId} · {gradeLabel(grade)} ({counts.questions} questions)
                      </option>
                    ))
                  )}
                </select>

                {starter.pack && (
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <p className="card-meta">
                      {starter.pack.items.length} questions covering{' '}
                      {starter.pack.coveredIndicators} of {starter.pack.indicators} indicators in this
                      subject-grade, with answers.
                    </p>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={importStarter}
                      disabled={starter.busy}
                    >
                      {starter.busy ? 'Importing…' : `Import all ${starter.pack.items.length}`}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

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
        <div className="card mb-4 flex flex-wrap items-center justify-between gap-3 border-brand-200 bg-brand-50 p-4 dark:border-brand-500/30 dark:bg-brand-500/15">
          <p className="text-sm text-brand-800 dark:text-brand-200">
            <span className="font-semibold">{selected.length}</span> selected · {totalMarks} marks
          </p>
          <div className="flex gap-2">
            <button type="button" className="btn-secondary" onClick={() => setSelected([])}>Clear</button>
            <button type="button" className="btn-accent" onClick={exportPaper}>Export exam paper (PDF)</button>
            <SaveToLibrary
              label="Save paper"
              kind="question_paper"
              filename={suggestFilename('question_paper', paperMeta(), 'pdf')}
              meta={paperMeta()}
              build={() => buildQuestionPaper(selectedQuestions, paperOptions()).output('blob')}
            />
          </div>
        </div>
      )}

      {error && <DataError what="questions" error={error} />}
{loading && <SkeletonList rows={4} />}
      {!loading && !error && visible.length === 0 && (
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
                className="mt-1 h-4 w-4 rounded border-line-2 text-brand-600"
                checked={selected.includes(question.id)}
                onChange={() => toggle(question)}
                aria-label={`Select "${question.prompt || question.question || question.id}" for the exam paper`}
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="chip">{TYPE_LABELS[question.type] || question.type}</span>
                  <span className="chip-brand">{gradeLabel(question.grade)}</span>
                  <span className="card-meta">{question.subjectName || question.subjectId}</span>
                  <span className="card-meta">{question.marks || 1} mark(s)</span>
                  {question.weekKey && <span className="card-meta">week {question.weekKey}</span>}
                </div>
                <p className="mt-2 text-sm text-text">{question.prompt || question.question}</p>
                {question.options?.length > 0 && (
                  <ol className="mt-2 space-y-1 text-sm text-muted">
                    {question.options.map((option, index) => (
                      <li key={index}>{String.fromCharCode(65 + index)}. {option}</li>
                    ))}
                  </ol>
                )}
                {question.answer && (
                  <p className="mt-2 rounded-lg bg-success-50 px-3 py-2 text-xs text-success-700 dark:bg-success-500/15 dark:text-success-500">
                    <span className="font-semibold">Answer: </span>{question.answer}
                  </p>
                )}
                <div className="mt-3 flex items-center gap-3">
                  <span className="card-meta">{question.authorName}</span>
                  {(question.authorId === user.uid || isAdmin) && (
                    <>
                      <Link to={`/portal/questions/${question.id}/edit`} className="text-xs font-semibold text-brand-700 hover:underline dark:text-brand-300">Edit</Link>
                      <button type="button" className="text-xs font-semibold text-danger-600 hover:underline dark:text-danger-500" onClick={() => setPendingDelete(question)}>Delete</button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>

      <LoadMore hasMore={hasMore} loading={loadingMore} error={moreError} onLoad={loadMore} loaded={rows.length} />

      <ConfirmModal open={Boolean(pendingDelete)} title="Delete this question?" confirmLabel="Delete" onConfirm={remove} onCancel={() => setPendingDelete(null)} />
    </div>
  )
}
