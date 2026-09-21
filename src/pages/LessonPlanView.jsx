import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDoc } from '../hooks/useCollection'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import { downloadLessonPlanDocx } from '../lib/lessonPlanDocx'
import { buildLessonPlanPdf, downloadLessonPlanPdf } from '../lib/lessonPlanPdf'
import SaveToLibrary from '../components/SaveToLibrary'
import { suggestFilename } from '../lib/generatedDocs'
import { useSchedules } from '../hooks/useCurriculum'
import { gradeLabel } from '../lib/grades'

const PHASES = [
  ['starter', 'Starter / introduction'],
  ['main', 'Main activities'],
  ['plenary', 'Plenary / conclusion'],
]

function Section({ heading, children }) {
  if (!children) return null
  return (
    <section className="mt-6">
      <h2 className="section-heading">{heading}</h2>
      <div className="mt-2 text-sm text-slate-700">{children}</div>
    </section>
  )
}

export default function LessonPlanView() {
  const { planId } = useParams()
  const { row: plan, loading, error } = useDoc('lesson_plans', planId)
  const { user, profile, isAdmin } = useAuth()
  const toast = useToast()
  const [busy, setBusy] = useState(null)
  // The planned subject's schedule. `subjectId` is always written by the form;
  // the indicator ids (`<subjectId>_<code>`) are the fallback for plans saved
  // before it was, so the term/day lookup does not silently go blank.
  const planSubject = plan?.subjectId
    || String((plan?.indicatorIds || [])[0] || '').split('_')[0]
    || null
  const { lessons } = useSchedules(plan?.grade, planSubject)

  if (loading) return <SkeletonList rows={2} />
  if (error) return <DataError what="this lesson plan" error={error} />
  if (!plan) {
    return (
      <EmptyState
        title="Lesson plan not found"
        message="It may have been deleted."
        action={<Link to="/portal/plans" className="btn-secondary mt-2">Back to plans</Link>}
      />
    )
  }

  const canEdit = plan.authorId === user.uid || isAdmin
  const meta = { school: profile?.school, teacher: profile?.name }
  // What the library records beside the file (P3-3), so the list is searchable.
  const libraryMeta = {
    subjectId: plan.subjectId, subjectName: plan.subjectName, grade: plan.grade,
    term: plan.term, week: plan.week, indicatorCodes: plan.indicatorCodes || [],
  }

  // Where this indicator sits in the term's schedule — handy before class.
  const scheduled = (lessons || []).filter((lesson) =>
    [lesson.indicatorCode, lesson.code].some((code) => code && (plan.indicatorCodes || []).includes(code))
  )

  const exportAs = async (kind) => {
    setBusy(kind)
    try {
      if (kind === 'docx') {
        const blob = await downloadLessonPlanDocx(plan, meta)
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `Lesson_Plan_${plan.subjectId}_${plan.grade}_W${plan.week || 1}.docx`
        link.click()
        URL.revokeObjectURL(url)
      } else {
        downloadLessonPlanPdf(plan, meta)
      }
      toast.success(`Exported ${kind === 'docx' ? 'Word document' : 'PDF'}`)
    } catch (error) {
      toast.error(`Export failed: ${error.message}`)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <Link to="/portal/plans" className="mb-6 inline-block text-sm text-slate-500 hover:text-slate-800">← Lesson plans</Link>

      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{plan.subjectName || plan.subjectId}</h1>
          <p className="page-subtitle">
            {gradeLabel(plan.grade)} · Term {plan.term}, week {plan.week} · {plan.durationMinutes || 60} minutes
            {(plan.indicatorCodes || []).length > 0 && ` · ${plan.indicatorCodes.join(', ')}`}
          </p>
          <p className="card-meta mt-1">by {plan.authorName}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" onClick={() => exportAs('docx')} disabled={busy}>
            {busy === 'docx' ? 'Preparing…' : 'Word (.docx)'}
          </button>
          <button type="button" className="btn-accent" onClick={() => exportAs('pdf')} disabled={busy}>
            {busy === 'pdf' ? 'Preparing…' : 'PDF'}
          </button>
          {/* Keep the file itself, not just the record (P3-3). Built lazily:
              the Word export only runs if a teacher presses this. */}
          <SaveToLibrary
            kind="lesson_plan"
            filename={suggestFilename('lesson_plan', libraryMeta, 'docx')}
            meta={libraryMeta}
            build={() => downloadLessonPlanDocx(plan, meta)}
          />
          <SaveToLibrary
            label="Save PDF"
            kind="lesson_plan"
            filename={suggestFilename('lesson_plan', libraryMeta, 'pdf')}
            meta={libraryMeta}
            build={() => buildLessonPlanPdf(plan, meta).output('blob')}
          />
          {canEdit && <Link to={`/portal/plans/${plan.id}/edit`} className="btn-primary">Edit</Link>}
        </div>
      </header>

      <div className="card p-6">
        <Section heading="Curriculum reference">
          {plan.strandName && <p><span className="font-medium">Strand:</span> {plan.strandName}</p>}
          {plan.subStrandName && <p><span className="font-medium">Sub-strand:</span> {plan.subStrandName}</p>}
          {plan.contentStandard && <p><span className="font-medium">Content standard:</span> {plan.contentStandard}</p>}
          {plan.indicatorDescription && <p><span className="font-medium">Indicator:</span> {plan.indicatorDescription}</p>}
          {plan.performanceIndicator && <p><span className="font-medium">Performance indicator:</span> {plan.performanceIndicator}</p>}
        </Section>

        <Section heading="Learning objectives">
          <ul className="list-disc space-y-1 pl-5">
            {(plan.objectives || []).map((objective, index) => <li key={index}>{objective}</li>)}
          </ul>
        </Section>

        <Section heading="Key words">
          {(plan.keywords || []).length > 0 && <p className="flex flex-wrap gap-2">{plan.keywords.map((word) => <span key={word} className="chip">{word}</span>)}</p>}
        </Section>

        <Section heading="Relevant previous knowledge">{plan.rpk}</Section>

        {PHASES.map(([key, heading]) =>
          plan[key]?.length ? (
            <Section key={key} heading={heading}>
              <ol className="list-decimal space-y-2 pl-5">
                {plan[key].map((step, index) => <li key={index}>{step}</li>)}
              </ol>
            </Section>
          ) : null
        )}

        <Section heading="Core competencies">
          <p>{[].concat(plan.competencies || []).join('; ')}</p>
        </Section>

        <Section heading="Teaching & learning materials">
          <p>{[].concat(plan.resources || []).join('; ')}</p>
        </Section>

        <Section heading="Assessment">{plan.assessment}</Section>
        <Section heading="Differentiation">{plan.differentiation}</Section>

        {scheduled.length > 0 && (
          <Section heading="When it falls in the term">
            <ul className="space-y-1">
              {scheduled.map((lesson, index) => (
                <li key={index} className="card-meta">
                  Term {lesson.term}, week {lesson.week}, day {lesson.day} — {lesson.sessionTitle || 'lesson'}
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </div>
  )
}
