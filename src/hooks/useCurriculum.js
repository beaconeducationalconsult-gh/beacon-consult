import { useEffect, useState } from 'react'

/*
 * Static curriculum JSON from /public/curriculum.
 *
 * Module-level caches mean each file is fetched at most once per session, so
 * navigating between grades is instant and offline browsing keeps working from
 * the service-worker cache. The caches are intentionally permanent: curriculum
 * data changes only on deploy, and the SW revalidates it in the background.
 */
const cache = new Map()
const scheduleCache = new Map()

/*
 * Resolve against the deploy base, not the domain root. Vite serves `public/`
 * at `BASE_URL` (always trailing-slashed: '/' at the root, '/app/' under a
 * sub-path such as a GitHub Pages project site or a reverse proxy). Hard-coding
 * '/curriculum/…' silently 404s anywhere but the root, and every dropdown fed
 * from it then renders empty — see src/components/SubjectSelect.jsx.
 */
const BASE_URL = import.meta.env.BASE_URL || '/'

const curriculumFile = (name) => `${BASE_URL}curriculum/${name}`

function loadJson(path, store) {
  if (store.has(path)) return store.get(path)
  const promise = fetch(path).then((res) => {
    if (!res.ok) {
      // Carry the status so callers can tell "this file does not exist"
      // (404 — normal for grades without schedules) from a real failure.
      const error = new Error(`Could not load ${path} (HTTP ${res.status})`)
      error.status = res.status
      throw error
    }
    return res.json()
  })
  store.set(path, promise)
  // Don't cache a rejected promise — let the next mount retry.
  promise.catch(() => store.delete(path))
  return promise
}

const gradeFile = (grade, kind) => curriculumFile(`${String(grade).toLowerCase()}_${kind}.json`)

export function useGrades() {
  const [state, setState] = useState({ loading: true, grades: [], error: null })

  useEffect(() => {
    let active = true
    // Only the async callback touches state — no synchronous setState in the
    // effect body (react-hooks/set-state-in-effect).
    loadJson(curriculumFile('grades.json'), cache)
      .then((grades) => active && setState({ loading: false, grades, error: null }))
      .catch((error) => active && setState({ loading: false, grades: [], error }))
    return () => {
      active = false
    }
  }, [])

  return state
}

export function useCurriculum(grade = 'B1') {
  const [state, setState] = useState({ grade: null, loading: true, subjects: [], indicators: [], error: null })

  useEffect(() => {
    let active = true
    Promise.all([
      loadJson(gradeFile(grade, 'subjects'), cache),
      loadJson(gradeFile(grade, 'indicators'), cache),
    ])
      .then(([subjects, indicators]) =>
        active && setState({ grade, loading: false, subjects, indicators, error: null })
      )
      .catch((error) =>
        active && setState({ grade, loading: false, subjects: [], indicators: [], error })
      )

    return () => {
      active = false
    }
  }, [grade])

  // While a new grade loads, report loading with empty data — derived, so
  // switching grades never leaves the previous grade's indicators on screen.
  const stale = state.grade !== grade
  return {
    grade,
    loading: stale || state.loading,
    subjects: stale ? [] : state.subjects,
    indicators: stale ? [] : state.indicators,
    error: stale ? null : state.error,
  }
}

export function useSchedules(grade) {
  const [state, setState] = useState({ grade: null, loading: true, lessons: [], error: null })

  useEffect(() => {
    if (!grade) return undefined
    let active = true
    loadJson(gradeFile(grade, 'schedules'), scheduleCache)
      .then((lessons) => active && setState({ grade, loading: false, lessons, error: null }))
      .catch((error) => {
        // A grade without a schedules file is normal (KG1/KG2 have none) —
        // anything else is a real failure and must not look like "no data".
        const absent = error?.status === 404
        active && setState({ grade, loading: false, lessons: [], error: absent ? null : error })
      })
    return () => {
      active = false
    }
  }, [grade])

  if (!grade) return { loading: false, lessons: [], error: null }
  const stale = state.grade !== grade
  return {
    loading: stale || state.loading,
    lessons: stale ? [] : state.lessons,
    error: stale ? null : state.error,
  }
}

/** True while an indicator is still an extraction placeholder. */
export function isPlaceholder(text) {
  if (!text) return true
  const t = String(text).trim().toLowerCase()
  return t === '' || t === 'n/a' || t.startsWith('placeholder') || t.includes('[to be completed')
}

/**
 * Nest flat indicators into strand → sub-strand → content standard → indicators.
 * Ordered by the numeric code segments where present, falling back to text.
 */
export function buildTree(indicators, subjectId) {
  const rows = indicators.filter((i) => !subjectId || i.subjectId === subjectId)
  const strands = new Map()

  for (const ind of rows) {
    const strandKey = ind.strandName || `Strand ${ind.strandNumber ?? '?'}`
    if (!strands.has(strandKey)) {
      strands.set(strandKey, { name: strandKey, number: ind.strandNumber ?? 0, subStrands: new Map() })
    }
    const strand = strands.get(strandKey)

    const subKey = ind.subStrandName || `Sub-strand ${ind.subStrandNumber ?? '?'}`
    if (!strand.subStrands.has(subKey)) {
      strand.subStrands.set(subKey, {
        name: subKey,
        number: ind.subStrandNumber ?? 0,
        standards: new Map(),
      })
    }
    const sub = strand.subStrands.get(subKey)

    const stdKey = ind.contentStandardCode || ind.code
    if (!sub.standards.has(stdKey)) {
      sub.standards.set(stdKey, {
        code: stdKey,
        description: ind.contentStandardDescription || '',
        indicators: [],
      })
    }
    sub.standards.get(stdKey).indicators.push(ind)
  }

  const byNumber = (a, b) => a.number - b.number
  return [...strands.values()]
    .sort(byNumber)
    .map((strand) => ({
      ...strand,
      subStrands: [...strand.subStrands.values()]
        .sort(byNumber)
        .map((sub) => ({
          ...sub,
          standards: [...sub.standards.values()].sort((a, b) => a.code.localeCompare(b.code)),
        })),
    }))
}
