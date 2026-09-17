import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

interface Subject {
  id: string
  name: string
  counts: {
    indicators: number
  }
}

export function GradePage() {
  const { grade } = useParams()
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!grade) return
    fetch(`/curriculum/${grade.toLowerCase()}_subjects.json`)
      .then((r) => r.json())
      .then((data) => setSubjects(data))
      .catch((e) => console.error('Error loading subjects:', e))
      .finally(() => setLoading(false))
  }, [grade])

  if (loading) return <div className="p-8 text-center">Loading subjects...</div>

  return (
    <div className="p-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">{grade} Subjects</h1>
        <p className="text-gray-600">Pick a subject to view the indicators.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
        {subjects.map((subject) => (
          <div key={subject.id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:border-[#C89B3C] transition-colors">
            <h2 className="text-xl font-bold mb-2">{subject.name}</h2>
            <p className="text-gray-600 mb-4">{subject.counts.indicators} indicators</p>
            <Link
              to={`/curriculum/${grade}/${subject.id}`}
              className="inline-block bg-[#1B4332] text-white px-4 py-2 rounded text-sm font-medium hover:bg-[#16201A] transition-colors"
            >
              View Indicators
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
