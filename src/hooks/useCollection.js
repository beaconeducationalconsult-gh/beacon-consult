import { useEffect, useState } from 'react'
import { collection, doc, limit as limitTo, onSnapshot, query, where } from 'firebase/firestore'
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
export function useCollection(name, { filters = [], sort = 'createdAt', max = 100, enabled = true } = {}) {
  const [state, setState] = useState({ loading: true, rows: [], error: null })
  const key = JSON.stringify(filters)

  useEffect(() => {
    if (!enabled) return undefined
    const clauses = filters.map(([field, op, value]) => where(field, op, value))
    const q = query(collection(db, name), ...clauses, limitTo(max))

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
  }, [name, key, sort, max, enabled])

  return enabled ? state : EMPTY
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
