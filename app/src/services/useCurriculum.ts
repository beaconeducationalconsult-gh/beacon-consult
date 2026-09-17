import { useEffect, useState } from 'react'
import type { Indicator } from '../kernel/types'

export function useIndicators(grade: string, subject: string) {
  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!grade || !subject) return
    setLoading(true)

    // The build script produces <grade>_indicators.json in /curriculum/
    fetch(`/curriculum/${grade.toLowerCase()}_indicators.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`No indicators found for grade ${grade}`)
        return r.json()
      })
      .then((data: any[]) => {
        // Filter by subjectId (e.g., 'mathematics')
        const filtered = data
          .filter((i) => i.subjectId === subject)
          .map((i) => ({
            code: i.code,
            strand: i.strandName,
            subStrand: i.subStrandName,
            contentStandard: i.contentStandardDescription,
            text: i.description,
            grade: i.grade,
            subject: i.subjectId,
            extra: i.extra ?? {},
          }))
        setIndicators(filtered)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [grade, subject])

  return { indicators, loading, error }
}
