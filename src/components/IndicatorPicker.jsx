import { useMemo, useState } from 'react'
import { useCurriculum } from '../hooks/useCurriculum'
import { gradeLabel } from '../lib/grades'
import { Skeleton } from './Skeleton'

/**
 * Choose one or more curriculum indicators (stored as `indicatorIds[]`, which
 * carries strand/sub-strand metadata back into the plan).
 * Extracted from LessonPlanForm — see docs/analysis/FINAL ANALYSIS.md.
 */
export default function IndicatorPicker({ grade, subjectId, selected = [], onChange }) {
  const { indicators, loading } = useCurriculum(grade)
  const [search, setSearch] = useState('')
  const [expandedStrand, setExpandedStrand] = useState(null)

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase()
    return indicators
      .filter((i) => !subjectId || i.subjectId === subjectId)
      .filter((i) =>
        !term ||
        String(i.code).toLowerCase().includes(term) ||
        String(i.description || '').toLowerCase().includes(term) ||
        String(i.strandName || '').toLowerCase().includes(term)
      )
  }, [indicators, subjectId, search])

  const strands = useMemo(() => {
    const grouped = new Map()
    for (const row of rows) {
      const key = row.strandName || 'Ungrouped'
      if (!grouped.has(key)) grouped.set(key, [])
      grouped.get(key).push(row)
    }
    return [...grouped.entries()]
  }, [rows])

  const isSelected = (row) => selected.some((s) => (s.indicatorId || s.code) === (row.id || row.code))

  const toggle = (row) => {
    const id = row.id || row.code
    if (isSelected(row)) {
      onChange(selected.filter((s) => (s.indicatorId || s.code) !== id))
    } else {
      onChange([
        ...selected,
        {
          indicatorId: id,
          code: row.code,
          description: row.description,
          strandName: row.strandName,
          subStrandName: row.subStrandName,
          contentStandard: row.contentStandardDescription || row.contentStandardCode,
        },
      ])
    }
  }

  if (loading) return <Skeleton className="h-40" />

  return (
    <div>
      {selected.length > 0 && (
        <ul className="mb-3 space-y-2">
          {selected.map((item) => (
            <li key={item.indicatorId} className="flex items-start justify-between gap-3 rounded-lg bg-brand-50 p-3">
              <span className="min-w-0">
                <span className="block font-mono text-xs font-semibold text-brand-700">{item.code}</span>
                <span className="block text-sm text-slate-700">{item.description}</span>
              </span>
              <button
                type="button"
                className="btn-ghost px-2 py-1 text-xs"
                onClick={() => onChange(selected.filter((s) => s.indicatorId !== item.indicatorId))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <input
        type="search"
        className="input"
        placeholder={`Search ${gradeLabel(grade)} indicators by code, strand or text…`}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="mt-3 max-h-80 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
        {strands.length === 0 && <p className="p-3 text-sm text-slate-500">No indicators match that search.</p>}
        {strands.map(([strand, items]) => {
          const open = expandedStrand === strand || Boolean(search.trim())
          return (
            <div key={strand}>
              <button
                type="button"
                aria-expanded={open}
                onClick={() => setExpandedStrand(open ? null : strand)}
                className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {strand}
                <span className="card-meta">{items.length}</span>
              </button>
              {open && (
                <ul className="space-y-1 pl-2">
                  {items.map((row) => (
                    <li key={row.id || row.code}>
                      <button
                        type="button"
                        onClick={() => toggle(row)}
                        aria-pressed={isSelected(row)}
                        className={`w-full rounded px-3 py-2 text-left text-sm transition-colors ${
                          isSelected(row) ? 'bg-brand-50 text-brand-800' : 'hover:bg-slate-50 text-slate-600'
                        }`}
                      >
                        <span className="font-mono text-xs">{row.code}</span>
                        <span className="mt-0.5 block">{row.description}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
