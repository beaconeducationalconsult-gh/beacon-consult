import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDoc } from '../hooks/useCollection'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { downloadSchemeDocx } from '../lib/schemeDocx'
import { downloadSchemePdf } from '../lib/schemePdf'
import { gradeLabel } from '../lib/grades'

export default function ForecastView() {
  const { forecastId } = useParams()
  const { row: scheme, loading } = useDoc('weekly_forecasts', forecastId)
  const { user, profile, isAdmin } = useAuth()
  const toast = useToast()
  const [busy, setBusy] = useState(null)

  if (loading) return <SkeletonList rows={2} />
  if (!scheme) {
    return (
      <EmptyState
        title="Scheme not found"
        message="It may have been deleted."
        action={<Link to="/portal/forecasts" className="btn-secondary mt-2">Back to schemes</Link>}
      />
    )
  }

  const canEdit = scheme.authorId === user.uid || isAdmin
  const meta = { school: profile?.school, teacher: profile?.name }

  const exportAs = async (kind) => {
    setBusy(kind)
    try {
      if (kind === 'docx') {
        const blob = await downloadSchemeDocx(scheme, meta)
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `Scheme_${scheme.subjectId}_${scheme.grade}_T${scheme.term}.docx`
        link.click()
        URL.revokeObjectURL(url)
      } else {
        downloadSchemePdf(scheme, meta)
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
      <Link to="/portal/forecasts" className="mb-6 inline-block text-sm text-slate-500 hover:text-slate-800">← Schemes</Link>

      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{scheme.subjectName || scheme.subjectId}</h1>
          <p className="page-subtitle">
            {gradeLabel(scheme.grade)} · Term {scheme.term} · {scheme.rows?.length || 0} weeks
            {scheme.visibility === 'public' && ' · shared with everyone'}
          </p>
          <p className="card-meta mt-1">by {scheme.authorName}</p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-secondary" onClick={() => exportAs('docx')} disabled={busy}>
            {busy === 'docx' ? 'Preparing…' : 'Word (.docx)'}
          </button>
          <button type="button" className="btn-accent" onClick={() => exportAs('pdf')} disabled={busy}>
            {busy === 'pdf' ? 'Preparing…' : 'PDF'}
          </button>
          {canEdit && <Link to={`/portal/forecasts/${scheme.id}/edit`} className="btn-primary">Edit</Link>}
        </div>
      </header>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[46rem] text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Wk</th>
              <th className="px-4 py-3">Strand / Sub-strand</th>
              <th className="px-4 py-3">Content standard</th>
              <th className="px-4 py-3">Indicators</th>
              <th className="px-4 py-3">Resources</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(scheme.rows || []).map((row, index) => (
              <tr key={index} className="align-top">
                <td className="px-4 py-3 font-semibold text-slate-700">{row.week ?? index + 1}</td>
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-800">{row.strandName}</p>
                  <p className="card-meta">{row.subStrandName}</p>
                </td>
                <td className="px-4 py-3 text-slate-600">{row.contentStandard || row.contentStandardDescription}</td>
                <td className="px-4 py-3">
                  <ul className="space-y-1">
                    {(row.indicatorCodes || []).map((code) => (
                      <li key={code} className="font-mono text-xs text-brand-700">{code}</li>
                    ))}
                  </ul>
                </td>
                <td className="px-4 py-3 text-slate-600">{row.resources}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {scheme.notes && (
        <div className="card mt-4 p-5">
          <p className="section-heading">Notes</p>
          <p className="mt-2 text-sm text-slate-600">{scheme.notes}</p>
        </div>
      )}
    </div>
  )
}
