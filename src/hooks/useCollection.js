import { useCallback, useEffect, useRef, useState } from 'react'
import {
  collection, doc, getDocs, limit as limitTo, onSnapshot, orderBy, query, startAfter, where,
} from 'firebase/firestore'
import { db } from '../firebase'

const EMPTY = { loading: false, rows: [], error: null }

/**
 * Live list of a collection with optional equality filters.
 *
 * Filters are passed as a plain array and keyed by JSON.stringify: a fresh
 * array literal on every render would otherwise resubscribe on every render.
 * Nothing is set synchronously inside the effect — Firestore's first snapshot
 * drives the loading flag, so there is no cascading render on mount.
 */
export function useCollection(name, { filters = [], sort = 'createdAt', max = 100, enabled = true, ordered = false } = {}) {
  const [state, setState] = useState({ loading: true, rows: [], error: null })
  const key = JSON.stringify(filters)

  useEffect(() => {
    if (!enabled) return undefined
    const clauses = filters.map(([field, op, value]) => where(field, op, value))
    // `ordered` is opt-in because ordering server-side is what makes a capped
    // list mean "the newest N" instead of "N arbitrary documents" — and, on a
    // filtered query, it needs a composite index (see firestore.indexes.json).
    const q = query(
      collection(db, name),
      ...clauses,
      ...(ordered ? [orderBy(sort, 'desc')] : []),
      limitTo(max)
    )

    return onSnapshot(
      q,
      (snap) => {
        const rows = snap.docs.map((d) => ({ id: d.id, ...d.data() }))
        if (sort) {
          rows.sort((a, b) => {
            const av = a[sort]?.seconds ?? a[sort] ?? 0
            const bv = b[sort]?.seconds ?? b[sort] ?? 0
            return bv > av ? 1 : bv < av ? -1 : 0
          })
        }
        setState({ loading: false, rows, error: null })
      },
      (error) => {
        // Degrade to an empty list rather than crashing the page; the rules and
        // the console error explain why. See docs/gotchas.md.
        console.warn(`[beacon] ${name} unavailable:`, error?.code || error)
        setState({ loading: false, rows: [], error })
      }
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, key, sort, max, enabled, ordered])

  return enabled ? state : EMPTY
}

/**
 * Live, **paged** list of a collection: the first page arrives by snapshot (so
 * a new row still appears without a reload), and `loadMore()` appends older
 * pages with a `startAfter` cursor.
 *
 * Why this exists: `max` on a single query is silent truncation. The cap is not
 * "the newest N" either — without `orderBy` Firestore returns documents in
 * internal-id order, so a busy collection quietly hides *arbitrary* rows and the
 * client-side sort only reorders what happened to arrive. Here the order is the
 * server's (`createdAt` descending), the page size is explicit, and `hasMore`
 * says whether more exists, so "no more data" and "not loaded yet" stop looking
 * the same.
 *
 * Every filtered query here needs its composite index — `where(field ==) +
 * orderBy(createdAt desc)` — in firestore.indexes.json. Without it Firestore
 * answers `failed-precondition`, which is what the page's DataError then shows.
 */
export function usePagedCollection(name, {
  filters = [], sort = 'createdAt', pageSize = 24, enabled = true,
} = {}) {
  const [state, setState] = useState({ loading: true, rows: [], error: null })
  // `extra` is keyed: a page loaded for the previous filter must not survive a
  // tab switch, and nothing may be written synchronously inside the effect.
  const [extra, setExtra] = useState({ key: null, rows: [] })
  const cursor = useRef(null)
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [moreError, setMoreError] = useState(null)
  const key = JSON.stringify({ filters, sort, pageSize })

  useEffect(() => {
    if (!enabled) return undefined
    const clauses = filters.map(([field, op, value]) => where(field, op, value))
    const q = query(
      collection(db, name),
      ...clauses,
      orderBy(sort, 'desc'),
      limitTo(pageSize),
    )

    return onSnapshot(
      q,
      (snap) => {
        cursor.current = snap.docs[snap.docs.length - 1] || null
        setHasMore(snap.size === pageSize)
        setExtra({ key, rows: [] })
        setState({
          loading: false,
          rows: snap.docs.map((d) => ({ id: d.id, ...d.data() })),
          error: null,
        })
      },
      (error) => {
        console.warn(`[beacon] ${name} unavailable:`, error?.code || error)
        setState({ loading: false, rows: [], error })
      }
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, key, enabled])

  const loadMore = useCallback(async () => {
    if (loadingMore || !cursor.current) return
    setLoadingMore(true)
    setMoreError(null)
    try {
      const clauses = filters.map(([field, op, value]) => where(field, op, value))
      const snap = await getDocs(query(
        collection(db, name),
        ...clauses,
        orderBy(sort, 'desc'),
        startAfter(cursor.current),
        limitTo(pageSize),
      ))
      cursor.current = snap.docs[snap.docs.length - 1] || cursor.current
      setHasMore(snap.size === pageSize)
      setExtra((current) => ({
        key,
        rows: [...(current.key === key ? current.rows : []), ...snap.docs.map((d) => ({ id: d.id, ...d.data() }))],
      }))
    } catch (error) {
      console.warn(`[beacon] ${name} page failed:`, error?.code || error)
      setMoreError(error)
    } finally {
      setLoadingMore(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, key, loadingMore, pageSize])

  if (!enabled) return { ...EMPTY, hasMore: false, loadingMore: false, loadMore: async () => {}, moreError: null }

  const appended = extra.key === key ? extra.rows : []
  const seen = new Set(state.rows.map((r) => r.id))
  return {
    ...state,
    rows: [...state.rows, ...appended.filter((r) => !seen.has(r.id))],
    hasMore,
    loadingMore,
    loadMore,
    moreError,
  }
}

/** Live single document (row === null when it does not exist). */
export function useDoc(name, id) {
  const [state, setState] = useState({ loading: true, row: null, error: null })

  useEffect(() => {
    if (!id) return undefined
    return onSnapshot(
      doc(db, name, id),
      (snap) => setState({ loading: false, row: snap.exists() ? { id: snap.id, ...snap.data() } : null, error: null }),
      (error) => {
        console.warn(`[beacon] ${name}/${id} unavailable:`, error?.code || error)
        setState({ loading: false, row: null, error })
      }
    )
  }, [name, id])

  return id ? state : EMPTY
}

/**
 * Deterministic id for indicator-linked docs — see `src/lib/docIds.js`.
 *
 * Re-exported here because this is where callers look for it; the implementation
 * lives in its own module so it can be tested without pulling in Firestore.
 */
export { indicatorDocId } from '../lib/docIds'
