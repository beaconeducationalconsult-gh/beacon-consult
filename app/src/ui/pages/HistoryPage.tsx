import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../services/AuthContext'
import { getGenerationHistory } from '../../services/firestore'

interface GenerationRecord {
  id: string
  subject: string
  grade: string
  indicatorCode: string
  documentType: string
  filename: string
  generatedAt: any
}

export function HistoryPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [history, setHistory] = useState<GenerationRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadHistory() {
      if (!user) return
      try {
        const schoolId = (user as any).schoolId ?? user.uid
        const data = await getGenerationHistory(schoolId)

        // Sort by date descending
        const sorted = data.sort((a, b) => {
          const dateA = a.generatedAt?.seconds ?? 0
          const dateB = b.generatedAt?.seconds ?? 0
          return dateB - dateA
        })
        setHistory(sorted)
      } catch (e) {
        console.error('Error loading history:', e)
      } finally {
        setLoading(false)
      }
    }
    loadHistory()
  }, [user])

  const handleRegenerate = (item: GenerationRecord) => {
    // Navigate to generator and pre-fill the indicator code
    navigate(`/generate?code=${item.indicatorCode}`)
  }

  if (loading) return <div className="p-8 text-center">Loading history...</div>
  if (!user) return <div className="p-8 text-center">Please sign in to view your history.</div>

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Generation History</h1>
        <p className="text-gray-600">All documents generated for your school.</p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead className="bg-gray-50">
            <tr>
              <th className="py-3 px-4 font-bold text-sm border-b border-gray-200">Date</th>
              <th className="py-3 px-4 font-bold text-sm border-b border-gray-200">Subject</th>
              <th className="py-3 px-4 font-bold text-sm border-b border-gray-200">Grade</th>
              <th className="py-3 px-4 font-bold text-sm border-b border-gray-200">Code</th>
              <th className="py-3 px-4 font-bold text-sm border-b border-gray-200">Type</th>
              <th className="py-3 px-4 font-bold text-sm border-b border-gray-200 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {history.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-gray-500">No documents found in your history.</td>
              </tr>
            ) : (
              history.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-4 text-sm">
                    {item.generatedAt?.seconds
                      ? new Date(item.generatedAt.seconds * 1000).toLocaleDateString()
                      : 'N/A'}
                  </td>
                  <td className="py-3 px-4 text-sm font-medium">{item.subject}</td>
                  <td className="py-3 px-4 text-sm">{item.grade}</td>
                  <td className="py-3 px-4 text-sm font-mono">{item.indicatorCode}</td>
                  <td className="py-3 px-4 text-sm">{item.documentType}</td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleRegenerate(item)}
                      className="text-xs bg-gray-100 text-gray-700 px-3 py-1 rounded hover:bg-gray-200 transition-colors font-medium"
                    >
                      Regenerate
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
