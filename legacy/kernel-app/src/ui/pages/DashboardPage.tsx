import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../services/AuthContext'
import { getSchool, getGenerationHistory } from '../../services/firestore'

interface GenerationRecord {
  id: string
  subject: string
  grade: string
  indicatorCode: string
  documentType: string
  filename: string
  generatedAt: any
}

export function DashboardPage() {
  const { user } = useAuth()
  const [schoolName, setSchoolName] = useState<string>('Your School')
  const [recentHistory, setRecentHistory] = useState<GenerationRecord[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDashboard() {
      if (!user) return

      try {
        const schoolId = (user as any).schoolId ?? user.uid

        // 1. Get School Name
        const school = await getSchool(schoolId)
        if (school?.name) setSchoolName(school.name)

        // 2. Get History
        const history = await getGenerationHistory(schoolId)

        // Sort by date descending
        const sorted = history.sort((a, b) => {
          const dateA = a.generatedAt?.seconds ?? 0
          const dateB = b.generatedAt?.seconds ?? 0
          return dateB - dateA
        })

        setTotalCount(sorted.length)
        setRecentHistory(sorted.slice(0, 5))
      } catch (e) {
        console.error('Error loading dashboard:', e)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [user])

  if (loading) return <div className="p-8 text-center">Loading dashboard...</div>
  if (!user) return <div className="p-8 text-center">Please sign in to view your dashboard.</div>

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-end mb-12">
        <div>
          <h1 className="text-4xl font-bold mb-2">{schoolName}</h1>
          <p className="text-gray-600">School Management Dashboard</p>
        </div>
        <Link
          to="/generate"
          className="bg-[#1B4332] text-white px-6 py-3 rounded-md font-bold hover:bg-[#16201A] transition-colors"
        >
          + Generate New
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 mb-1">Total Documents</p>
          <p className="text-3xl font-bold">{totalCount}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 mb-1">This Term</p>
          <p className="text-3xl font-bold">{totalCount}</p>
          <p className="text-xs text-gray-400 mt-1">All-time stats</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 mb-1">Active Grade</p>
          <p className="text-3xl font-bold">B4</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="font-bold">Recent Generations</h2>
          <Link to="/history" className="text-sm text-[#1B4332] hover:underline">View All</Link>
        </div>
        <div className="divide-y divide-gray-100">
          {recentHistory.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No documents generated yet.</div>
          ) : (
            recentHistory.map((item) => (
              <div key={item.id} className="px-6 py-4 flex justify-between items-center hover:bg-gray-50 transition-colors">
                <div>
                  <p className="font-medium">{item.subject} — {item.grade}</p>
                  <p className="text-xs text-gray-500">{item.indicatorCode} • {item.documentType}</p>
                </div>
                <Link
                  to="/history"
                  className="text-sm text-gray-600 hover:text-[#1B4332]"
                >
                  Details →
                </Link>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
