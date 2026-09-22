import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDoc } from '../hooks/useCollection'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import { downloadSchemeDocx } from '../lib/schemeDocx'
import { buildSchemePdf, downloadSchemePdf } from '../lib/schemePdf'
import SaveToLibrary from '../components/SaveToLibrary'
import { BackLink } from '../ui'
import { suggestFilename } from '../lib/generatedDocs'
import { gradeLabel } from '../lib/grades'

export default function ForecastView() {
  const { forecastId } = useParams()
  const { row: scheme, loading, error } = useDoc('weekly_forecasts', forecastId)
  const { user, profile, isAdmin } = useAuth()
  const toast = useToast()
  const [busy, setBusy] = useState(null)

  if (loading) return <SkeletonList rows={2} />
  if (error) return <DataError what="this scheme" error={error} />
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
  const libraryMeta = {
    subjectId: scheme.subjectId, subjectName: scheme.subjectName,
    grade: scheme.grade, term: scheme.term, weeks: scheme.rows?.length,
  }

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
      <BackLink to="/portal/forecasts" className="mb-6">Schemes</BackLink>

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
          <SaveToLibrary
            kind="scheme"
            filename={suggestFilename('scheme', libraryMeta, 'docx')}
            meta={libraryMeta}
            build={() => downloadSchemeDocx(scheme, meta)}
          />
          <SaveToLibrary
            label="Save PDF"
            kind="scheme"
            filename={suggestFilename('scheme', libraryMeta, 'pdf')}
            meta={libraryMeta}
            build={() => buildSchemePdf(scheme, meta).output('blob')}
          />
          {canEdit && <Link to={`/portal/forecasts/${scheme.id}/edit`} className="btn-primary">Edit</Link>}
        </div>
      </header>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[46rem] text-sm">
          <thead className="bg-surface-2 text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Wk</th>
              <th className="px-4 py-3">Strand / Sub-strand</th>
              <th className="px-4 py-3">Content standard</th>
              <th className="px-4 py-3">Indicators</th>
              <th className="px-4 py-3">Resources</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {(scheme.rows || []).map((row, index) => (
              <tr key={index} className="align-top">
                <td className="px-4 py-3 font-semibold text-text">{row.week ?? index + 1}</td>
                <td className="px-4 py-3">
                  <p className="font-medium text-heading">{row.strandName}</p>
                  <p className="card-meta">{row.subStrandName}</p>
                </td>
                <td className="px-4 py-3 text-text">{row.contentStandard || row.contentStandardDescription}</td>
                <td className="px-4 py-3">
                  <ul className="space-y-1">
                    {(row.indicatorCodes || []).map((code) => (
                      <li key={code} className="font-mono text-xs text-brand-700 dark:text-brand-300">{code}</li>
                    ))}
                  </ul>
                </td>
                <td className="px-4 py-3 text-text">{row.resources}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {scheme.notes && (
        <div className="card mt-4 p-5">
          <p className="section-heading">Notes</p>
          <p className="mt-2 text-sm text-text">{scheme.notes}</p>
        </div>
      )}
    </div>
  )
}
