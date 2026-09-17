import { useParams, Link } from 'react-router-dom'
import { useIndicators } from '../../services/useCurriculum'

export function IndicatorListPage() {
  const { grade, subject } = useParams()
  const { indicators, loading, error } = useIndicators(grade!, subject!)

  if (loading) return <div className="p-8 text-center">Loading indicators...</div>
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>

  return (
    <div className="p-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">{subject} — {grade}</h1>
        <p className="text-gray-600">Detailed indicators for this subject and grade.</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="py-3 px-4 font-bold text-sm">Code</th>
              <th className="py-3 px-4 font-bold text-sm">Strand</th>
              <th className="py-3 px-4 font-bold text-sm">Description</th>
              <th className="py-3 px-4 font-bold text-sm text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {indicators.map((ind) => (
              <tr key={ind.code} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="py-3 px-4 text-sm font-mono">{ind.code}</td>
                <td className="py-3 px-4 text-sm">{ind.strand}</td>
                <td className="py-3 px-4 text-sm">{ind.text}</td>
                <td className="py-3 px-4 text-right">
                  <Link
                    to={`/generate?code=${ind.code}`}
                    className="bg-[#1B4332] text-white px-3 py-1 rounded text-xs font-medium hover:bg-[#16201A] transition-colors"
                  >
                    Generate Lesson Plan
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
