import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface Grade {
  id: string
  name: string
  available: boolean
  subjects: number
}

export function CurriculumPage() {
  const [grades, setGrades] = useState<Grade[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/curriculum/grades.json')
      .then((r) => r.json())
      .then((data) => setGrades(data))
      .catch((e) => console.error('Error loading grades:', e))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-center">Loading curriculum...</div>

  return (
    <div className="p-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Curriculum Browser</h1>
        <p className="text-gray-600">Select a grade to explore available subjects and indicators.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {grades.map((grade) => (
          <div key={grade.id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:border-[#C89B3C] transition-colors">
            <h2 className="text-xl font-bold mb-2">{grade.name}</h2>
            <p className="text-gray-600 mb-4">{grade.subjects} subjects available</p>
            <Link
              to={`/curriculum/${grade.id}`}
              className="inline-block bg-[#1B4332] text-white px-4 py-2 rounded text-sm font-medium hover:bg-[#16201A] transition-colors"
            >
              Explore Grade
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
