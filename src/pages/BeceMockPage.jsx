import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import SaveToLibrary from '../components/SaveToLibrary'
import { useAuth } from '../context/AuthContext'
import { BECE_FORMAT, composeBecePaper } from '../lib/becePaper'
import { buildBecePaper, downloadBecePaper } from '../lib/becePdf'
import { suggestFilename } from '../lib/generatedDocs'
import { loadStarterPack } from '../lib/starterBank'

/*
 * BECE mock papers — mathematics (P3-6).
 *
 * The exam builder composes *a* paper from whatever a teacher has, scoped to
 * one subject-grade and term. This page composes *the* paper: WAEC's BECE
 * mathematics format, drawn from the whole served JHS bank (B7–B9), the years
 * the exam actually examines — so a B9 teacher can print a full 100-mark mock
 * without selecting anything. Composition lives in `src/lib/becePaper.js` and
 * is pure; this page is the loading, the honesty lines and the exports.
 *
 * Nothing is written to Firestore — like the exam builder, the paper is the
 * PDF (persisting it is the deferred next step, see docs/TODO.md P3-6).
 */

const JHS = ['B7', 'B8', 'B9']

export default function BeceMockPage() {
  const { profile } = useAuth()
  const [packs, setPacks] = useState(null) // null = loading; [] = none of the bank arrived
  const [school, setSchool] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.all(JHS.map((grade) => loadStarterPack('mathematics', grade)))
      .then((loaded) => {
        if (cancelled) return
        const arrived = loaded
          .map((pack, index) => ({ grade: JHS[index], items: pack?.items || [] }))
        setPacks(arrived.some((pack) => pack.items.length) ? arrived : [])
      })
      .catch(() => !cancelled && setPacks([]))
    return () => { cancelled = true }
  }, [])

  const paper = useMemo(
    () => (packs?.length ? composeBecePaper(packs) : null),
    [packs],
  )

  const options = () => ({ school: school.trim() || profile?.schoolName || undefined })

  const meta = () => ({
    kind: 'question_paper',
    title: 'BECE mock — Mathematics',
    subjectId: 'mathematics',
    subjectName: 'Mathematics',
    grade: 'B7–B9',
    term: 'all',
    totalMarks: paper?.totalMarks,
  })

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">BECE mock — Mathematics</h1>
          <p className="mt-1 text-sm text-slate-600">
            The WAEC format from the whole JHS bank: Paper 1 objectives and Paper 2
            structured questions, composed from B7&ndash;B9 together — the years the exam examines.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary" to="/portal/questions/exam">Exam builder instead</Link>
          <Link className="btn-primary" to="/portal/questions/new">New question</Link>
        </div>
      </div>

      {packs === null && <p className="card-meta">Loading the served JHS bank…</p>}

      {packs?.length === 0 && (
        <EmptyState
          title="The served bank has no JHS mathematics yet"
          message="This page composes from the bundle's starter bank (public/curriculum/questions). Install a bundle that carries it, or import the bank from the question bank page first."
        />
      )}

      {paper && (
        <>
          <div className="card mb-5 p-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <p className="label-caps">Paper 1 — Objective</p>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold">{paper.paper1.questions.length}</span> questions
                  {' '}· {paper.paper1.marks} marks · {paper.paper1.minutes} minutes
                </p>
                <p className="card-meta">
                  {Object.entries(paper.paper1.gradeSpread).map(([grade, n]) => `${grade} ${n}`).join(' · ')}
                  {` — from ${paper.paper1.indicators} indicators`}
                </p>
              </div>
              <div>
                <p className="label-caps">Paper 2 — Essay</p>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold">{paper.paper2.questions.length}</span> questions
                  {' '}of {BECE_FORMAT.paper2.marksEach} · answer {paper.paper2.answerCount}
                  {' '}· {paper.paper2.marks} marks · {paper.paper2.minutes} minutes
                </p>
                <p className="card-meta">
                  parts lettered (a), (b)… — marks read down the margin like the print
                </p>
              </div>
              <div>
                <p className="label-caps">The whole sitting</p>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold">{paper.totalMarks} marks</span> · 2 hours
                </p>
                <p className="card-meta">{paper.indicators} indicators asked in all</p>
              </div>
            </div>

            {paper.shortfalls.length > 0 && (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                {paper.shortfalls.map((line) => <p key={line}>{line}</p>)}
              </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button type="button" className="btn-secondary" onClick={() => downloadBecePaper(paper, { ...options(), includeAnswers: false })}>
                Student copy (PDF)
              </button>
              <button type="button" className="btn-accent" onClick={() => downloadBecePaper(paper, { ...options(), includeAnswers: true })}>
                Teacher copy + marking scheme
              </button>
              <SaveToLibrary
                label="Save paper"
                kind="question_paper"
                filename={suggestFilename('question_paper', meta(), 'pdf')}
                meta={meta()}
                build={() => buildBecePaper(paper, { ...options(), includeAnswers: true }).output('blob')}
              />
            </div>
            <input
              className="input mt-3 sm:max-w-xs"
              placeholder="School on the paper (optional)"
              value={school}
              onChange={(e) => setSchool(e.target.value)}
            />
          </div>

          <div className="card p-4">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Paper 2 as composed</h2>
            <ol className="space-y-3">
              {paper.paper2.questions.map((question) => (
                <li key={question.id} className="rounded-lg border border-slate-200 p-3">
                  <p className="text-sm font-semibold text-slate-900">
                    Question {question.number}
                    <span className="ml-2 font-normal text-slate-500">
                      {question.grade} · strand {question.strand.split('.')[1]} · {question.marks} marks
                    </span>
                  </p>
                  <ul className="mt-1 space-y-0.5">
                    {question.parts.map((part) => (
                      <li key={part.question.id} className="text-sm text-slate-700">
                        <span className="font-semibold">({part.letter})</span> {part.question.prompt}
                        <span className="ml-1 text-slate-400">[{part.marks}]</span>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-semibold text-brand-700">
                Paper 1 — all {paper.paper1.questions.length} objectives
              </summary>
              <ol className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
                {paper.paper1.questions.map((question, index) => (
                  <li key={question.id} className="text-sm text-slate-700">
                    {index + 1}. {question.prompt}
                  </li>
                ))}
              </ol>
            </details>
          </div>
        </>
      )}
    </div>
  )
}
