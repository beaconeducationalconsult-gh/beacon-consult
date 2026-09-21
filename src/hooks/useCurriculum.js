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

/*
 * Schedules are one file per subject-grade (`schedules/b3-mathematics.json`),
 * not one per grade. The combined per-grade file was 3.5-4.8 MB and every
 * caller wants exactly one subject's worth — a scheme for one subject and term,
 * the week an indicator falls in, the lessons behind a plan. Split, the same
 * screen fetches ~0.5 MB, and the service worker caches that one file for
 * offline use instead of a whole grade.
 */
const scheduleFile = (grade, subjectId) =>
  curriculumFile(`schedules/${String(grade).toLowerCase()}-${subjectId}.json`)

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

export function useSchedules(grade, subjectId) {
  const key = grade && subjectId ? `${grade}|${subjectId}` : null
  const [state, setState] = useState({ key: null, loading: true, lessons: [], error: null })

  useEffect(() => {
    if (!key) return undefined
    let active = true
    loadJson(scheduleFile(grade, subjectId), scheduleCache)
      .then((lessons) => active && setState({ key, loading: false, lessons, error: null }))
      .catch((error) => {
        // A subject-grade without schedules is normal (KG1/KG2 have none, and
        // not every subject is scheduled) — anything else is a real failure and
        // must not look like "no data".
        const absent = error?.status === 404
        active && setState({ key, loading: false, lessons: [], error: absent ? null : error })
      })
    return () => {
      active = false
    }
  }, [key, grade, subjectId])

  if (!key) return { loading: false, lessons: [], error: null }
  const stale = state.key !== key
  return {
    loading: stale || state.loading,
    lessons: stale ? [] : state.lessons,
    error: stale ? null : state.error,
  }
}

/**
 * Every scheduled lesson in a grade, for the one screen that shows all subjects
 * at once (the term calendar). Fetches the per-subject files in parallel and
 * appends each as it lands, so the calendar fills in rather than blocking on
 * ~5 MB. The service worker caches each file, so a second visit is offline-fast.
 */
export function useGradeSchedules(grade) {
  const { subjects } = useCurriculum(grade)
  const ids = subjects.filter((s) => s.hasSchedule).map((s) => s.id).join(',')
  const key = grade && ids ? `${grade}|${ids}` : null
  const [state, setState] = useState({ key: null, lessons: [], loading: true, error: null })

  useEffect(() => {
    if (!key) return undefined
    let active = true
    // No synchronous reset here (react-hooks/set-state-in-effect): the first
    // arrival adopts the new key, and a stale key renders as "still loading".
    const adopt = (update) => setState((current) => (current.key === key
      ? { ...current, ...update }
      : { key, lessons: [], loading: true, error: null, ...update }))
    const pending = ids.split(',').map((subjectId) =>
      loadJson(scheduleFile(grade, subjectId), scheduleCache)
        .then((lessons) => {
          if (active) {
            setState((current) => (current.key === key
              ? { ...current, lessons: [...current.lessons, ...lessons] }
              : { key, lessons, loading: true, error: null }))
          }
        })
        .catch((error) => {
          // A subject with no schedules file is normal; anything else is real.
          if (active && error?.status !== 404) adopt({ error })
        })
    )
    Promise.all(pending).then(() => {
      // Every file settled: adopt the key even if none of them produced rows,
      // so a grade with no readable schedules stops looking like it is loading.
      if (active) adopt({ loading: false })
    })
    return () => {
      active = false
    }
  }, [key, grade, ids])

  if (!key) return { loading: false, lessons: [], error: null }
  const current = state.key === key
  return {
    loading: !current || state.loading,
    lessons: current ? state.lessons : [],
    error: current ? state.error : null,
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
