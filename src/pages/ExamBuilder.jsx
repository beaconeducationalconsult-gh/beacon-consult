import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum } from '../hooks/useCurriculum'
import { usePagedCollection } from '../hooks/useCollection'
import LoadMore from '../components/LoadMore'
import SubjectSelect from '../components/SubjectSelect'
import EmptyState from '../components/EmptyState'
import SaveToLibrary from '../components/SaveToLibrary'
import { GRADES, TERMS, gradeLabel } from '../lib/grades'
import { buildQuestionPaper, downloadQuestionPaper } from '../lib/questionPaper'
import { buildPool, composePaper, summarise } from '../lib/examPaper'
import { loadStarterPack } from '../lib/starterBank'
import { suggestFilename } from '../lib/generatedDocs'

const TYPE_LABELS = { mcq: 'Objective', short: 'Short answer', essay: 'Essay', truefalse: 'True / false' }

/**
 * Exam paper builder.
 *
 * The bank's `Export exam paper` button prints whatever the teacher has ticked;
 * this page decides *what* to tick. It draws on two pools at once — the
 * questions already in the bank, and the served starter bank for the chosen
 * subject-grade, which is the only content that exists at all for B7–B9 until
 * someone writes their own — and assembles a paper of a requested size with the
 * coverage rule in `src/lib/examPaper.js` (one question per indicator before
 * any indicator is asked twice).
 *
 * It is deliberately a *builder*, not an author: nothing is written to
 * Firestore here. The paper is a PDF, and the teacher copy carries the marking
 * scheme, which is what `questionPaper.js` has always printed.
 */
export default function ExamBuilder() {
  const { user, profile } = useAuth()
  const toast = useToast()
  const [grade, setGrade] = useState('B7')
  const [subjectId, setSubjectId] = useState('')
  const [term, setTerm] = useState(1)
  const [targetMarks, setTargetMarks] = useState(50)
  const [duration, setDuration] = useState(120)
  const [school, setSchool] = useState('')
  // The served bank of the subject-grade currently on screen. Keyed, so a pack
  // fetched for the previous subject is never shown as if it were this one's —
  // and the effect never has to clear state synchronously, which the
  // react-hooks/set-state-in-effect rule (rightly) refuses.
  const [starterPack, setStarterPack] = useState(null)
  const [dropped, setDropped] = useState([])
  const [paper, setPaper] = useState(null)

  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(grade)
  // The member's own questions, newest first, filtered to this paper below. The
  // filters are client-side on purpose: two equality filters on Firestore would
  // need another composite index, and a teacher building a paper can page for
  // the questions they want anyway.
  const {
    rows: myQuestions, loading: loadingMine, hasMore, loadingMore, loadMore,
  } = usePagedCollection('questions', { pageSize: 50 })

  const mine = useMemo(
    () => myQuestions.filter((q) => q.grade === grade && q.subjectId === subjectId),
    [myQuestions, grade, subjectId]
  )

  // The served bank is a static file: fetch it when the subject-grade changes,
  // never on page load.
  const starterKey = `${grade}|${subjectId}`
  const starter = starterPack?.key === starterKey ? starterPack.items : null
  const starterState = !subjectId
    ? 'idle'
    : starter
      ? (starter.length ? 'ready' : 'none')
      : 'loading'

  useEffect(() => {
    if (!subjectId) return undefined
    let alive = true
    const key = `${grade}|${subjectId}`
    loadStarterPack(subjectId, grade).then((pack) => {
      if (alive) setStarterPack({ key, items: pack?.items || [] })
    })
    return () => { alive = false }
  }, [subjectId, grade])

  const subjectName = subjects.find((s) => s.id === subjectId)?.name || subjectId

  const pool = useMemo(
    () => buildPool(mine, starter || []).filter((q) => !dropped.includes(q.id)),
    [mine, starter, dropped]
  )
  const summary = useMemo(() => summarise(pool), [pool])

  const build = () => {
    if (!subjectId) return toast.error('Choose a subject first.')
    if (!pool.length) return toast.error('There are no questions for this subject-grade yet.')
    setPaper(composePaper(pool, { targetMarks: Number(targetMarks) || 50 }))
  }

  const options = () => ({
    subjectName,
    grade,
    term: Number(term) || 1,
    totalMarks: paper?.totalMarks,
    durationMinutes: Number(duration) || 120,
    school: school.trim() || undefined,
  })

  const meta = () => ({
    grade,
    subjectId,
    subjectName,
    term: Number(term) || 1,
    questions: paper?.questions.length || 0,
    totalMarks: paper?.totalMarks || 0,
    durationMinutes: Number(duration) || 120,
    // Which pool each question came from, so the library record says whether
    // this paper is built on the served bank or on the teacher's own writing.
    starterQuestions: paper?.questions.filter((q) => q.source?.startsWith('generated')).length || 0,
    authoredBy: profile?.name || 'Member',
    userId: user?.uid,
  })

  const drop = (id) => {
    setDropped((current) => [...current, id])
    // Recompose straight away: the point of dropping one is to see what the
    // paper becomes, and the composition is pure, so this is cheap.
    const next = buildPool(mine, starter || []).filter((q) => ![...dropped, id].includes(q.id))
    setPaper(composePaper(next, { targetMarks: Number(targetMarks) || 50 }))
  }

  const [sectionA, sectionB, sectionC] = paper?.sections || []

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Exam paper builder</h1>
          <p className="page-subtitle">
            Assemble a paper from the served question bank and your own questions. The teacher
            copy carries the marking scheme.
          </p>
        </div>
        <Link to="/portal/questions" className="btn-secondary">Back to the bank</Link>
      </header>

      <div className="card mb-5 space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label-caps" htmlFor="exam-grade">Grade</label>
            <select
              id="exam-grade"
              className="input"
              value={grade}
              onChange={(e) => { setGrade(e.target.value); setSubjectId(''); setPaper(null); setDropped([]) }}
            >
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="exam-subject">Subject</label>
            <SubjectSelect
              id="exam-subject"
              grade={grade}
              subjects={subjects}
              loading={loadingSubjects}
              error={subjectsError}
              value={subjectId}
              onChange={(e) => { setSubjectId(e.target.value); setPaper(null); setDropped([]) }}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="exam-term">Term</label>
            <select id="exam-term" className="input" value={term} onChange={(e) => setTerm(e.target.value)}>
              {TERMS.map((t) => <option key={t} value={t}>Term {t}</option>)}
            </select>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label-caps" htmlFor="exam-marks">Target total marks</label>
            <input
              id="exam-marks"
              type="number"
              min="10"
              step="5"
              className="input"
              value={targetMarks}
              onChange={(e) => setTargetMarks(e.target.value)}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="exam-duration">Duration (minutes)</label>
            <input
              id="exam-duration"
              type="number"
              min="30"
              step="15"
              className="input"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="exam-school">School on the paper (optional)</label>
            <input
              id="exam-school"
              className="input"
              placeholder="e.g. Beacon Basic School"
              value={school}
              onChange={(e) => setSchool(e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn-primary" onClick={build} disabled={!subjectId}>
            {paper ? 'Rebuild paper' : 'Build paper'}
          </button>
          {paper && (
            <button type="button" className="btn-secondary" onClick={() => { setPaper(null); setDropped([]) }}>
              Clear paper
            </button>
          )}
          {subjectId && (
            <p className="card-meta">
              {loadingMine ? 'Loading your questions…' : `${mine.length} of yours`}
              {starterState === 'loading' && ' · loading the served bank…'}
              {starterState === 'ready' && ` · ${starter.length} from the served bank`}
              {starterState === 'none' && ' · the served bank has none for this subject-grade'}
              {mine.length + (starter?.length || 0) > 0 && ` — ${summarise(buildPool(mine, starter || [])).marks} marks to choose from`}
            </p>
          )}
        </div>

        {subjectId && hasMore && (
          <LoadMore onClick={loadMore} loading={loadingMore} label="Load more of your questions" />
        )}
      </div>

      {paper && (
        <>
          <div className="card mb-5 flex flex-wrap items-center justify-between gap-3 border-brand-200 bg-brand-50 p-4">
            <p className="text-sm text-brand-800">
              <span className="font-semibold">{paper.questions.length}</span> questions ·{' '}
              <span className="font-semibold">{paper.totalMarks}</span> marks of {paper.targetMarks} asked
              {paper.targetMarks - paper.totalMarks > 0 && (
                <> · {paper.targetMarks - paper.totalMarks} marks short (no single question fitted the gap)</>
              )}{' '}
              · {paper.indicators} indicators covered
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => downloadQuestionPaper(paper.questions, { ...options(), includeAnswers: false })}
              >
                Student copy (PDF)
              </button>
              <button
                type="button"
                className="btn-accent"
                onClick={() => downloadQuestionPaper(paper.questions, { ...options(), includeAnswers: true })}
              >
                Teacher copy + marking scheme
              </button>
              <SaveToLibrary
                label="Save paper"
                kind="question_paper"
                filename={suggestFilename('question_paper', meta(), 'pdf')}
                meta={meta()}
                build={() => buildQuestionPaper(paper.questions, { ...options(), includeAnswers: true }).output('blob')}
              />
            </div>
          </div>

          {paper.omitted.length > 0 && (
            <div className="card mb-5 border-amber-200 bg-amber-50 p-4">
              <p className="card-meta text-amber-800">
                {paper.omitted.map((section) => (
                  <span key={section.id} className="block">
                    <span className="font-semibold">{section.label} is not on this paper:</span>{' '}
                    {section.reason}. Raise the target marks, or write a shorter question for it.
                  </span>
                ))}
              </p>
            </div>
          )}

          {[sectionA, sectionB, sectionC].filter(Boolean).map((section) => (
            <section key={section.id} className="card mb-5 p-6">
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="section-heading">{section.label}</h2>
                <p className="card-meta">{section.marks} marks</p>
              </div>
              <p className="card-meta mb-4">{section.instructions}</p>
              {section.questions.length === 0 ? (
                <p className="card-meta">No question of this kind in the pool.</p>
              ) : (
                <ol className="space-y-3">
                  {section.questions.map((question, index) => (
                    <li key={question.id} className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3 last:border-0">
                      <div>
                        <p className="text-sm text-slate-800">
                          <span className="font-semibold">{section.id}{index + 1}.</span> {question.prompt}
                        </p>
                        {question.options?.length > 0 && (
                          <p className="card-meta mt-1">
                            {question.options.map((opt, i) => `${String.fromCharCode(65 + i)}. ${opt}`).join('   ')}
                          </p>
                        )}
                        <p className="card-meta mt-1">
                          {question.indicatorCode || question.indicatorCodes?.[0] || 'no indicator'} ·{' '}
                          {TYPE_LABELS[question.type] || question.type} · {question.marks ?? 1} mark(s)
                          {question.source?.startsWith('generated') && ' · served bank'}
                          {question.source === 'authored' && ' · authored'}
                        </p>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary shrink-0 text-xs"
                        onClick={() => drop(question.id)}
                      >
                        Drop
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          ))}

          {summary.unplaced > 0 && (
            <p className="card-meta mb-5">
              {summary.unplaced} question(s) in the pool have a type no section claims, so they are
              not on the paper. Edit them in the bank if they should be.
            </p>
          )}
        </>
      )}

      {!paper && (
        <EmptyState
          title="No paper yet"
          message="Choose a grade and subject, then build a paper. Nothing is written to the database — the paper is a PDF, and the teacher copy carries the answers."
          action={<Link to="/portal/questions" className="btn-secondary mt-2">Browse the question bank</Link>}
        />
      )}
    </div>
  )
}
