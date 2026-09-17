import { useEffect, useState } from 'react'
import { collection, doc, onSnapshot, setDoc, increment, arrayUnion, arrayRemove } from 'firebase/firestore'
import { db } from '../firebase'

const quotesCache = new Map()

function loadJson(path) {
  if (quotesCache.has(path)) return quotesCache.get(path)
  const promise = fetch(path).then((res) => {
    if (!res.ok) throw new Error(`Could not load ${path} (HTTP ${res.status})`)
    return res.json()
  })
  promise.catch(() => quotesCache.delete(path))
  quotesCache.set(path, promise)
  return promise
}

function useJson(path) {
  const [state, setState] = useState({ loading: true, data: [] })
  useEffect(() => {
    let active = true
    loadJson(path)
      .then((data) => active && setState({ loading: false, data }))
      .catch(() => active && setState({ loading: false, data: [] }))
    return () => {
      active = false
    }
  }, [path])
  return state
}

export const useQuotes = () => useJson('/quotes/quotes.json')
export const useTheories = () => useJson('/quotes/theories.json')

/** Stable per local day, so everyone sees the same pick and it changes at local midnight. */
export function dailyIndex(length) {
  if (!length) return 0
  const now = new Date()
  const dayNumber = Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000)
  return dayNumber % length
}

export function quoteOfTheDay(quotes = []) {
  return quotes.length ? quotes[dailyIndex(quotes.length)] : null
}

export function theoryOfTheWeek(theories = []) {
  if (!theories.length) return null
  const now = new Date()
  const dayNumber = Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000)
  return theories[Math.floor(dayNumber / 7) % theories.length]
}

/**
 * Shared likes for static quote content. One live listener on the whole
 * collection; the error callback keeps it degrading gracefully when the
 * collection is empty or the reader is not signed in.
 */
export function useQuoteLikes() {
  const [likes, setLikes] = useState({})

  useEffect(() => {
    return onSnapshot(
      collection(db, 'quote_likes'),
      (snap) => {
        const next = {}
        snap.forEach((d) => {
          next[d.id] = { id: d.id, ...d.data() }
        })
        setLikes(next)
      },
      (error) => {
        console.warn('[beacon] quote_likes unavailable:', error?.code || error)
        setLikes({})
      }
    )
  }, [])

  return likes
}

export async function toggleQuoteLike(quoteId, uid, likes) {
  const entry = likes?.[quoteId]
  const ref = doc(db, 'quote_likes', quoteId)
  const liked = Boolean(entry?.likedBy?.includes(uid))

  if (!entry) {
    await setDoc(ref, { count: 1, likedBy: [uid] })
    return
  }
  if (liked) {
    await setDoc(
      ref,
      { count: increment(-1), likedBy: arrayRemove(uid) },
      { merge: true }
    )
  } else {
    await setDoc(
      ref,
      { count: increment(1), likedBy: arrayUnion(uid) },
      { merge: true }
    )
  }
}

export function topLikedQuotes(quotes = [], likes = {}, n = 5) {
  return quotes
    .map((q) => ({ ...q, likes: likes[q.id]?.count || 0 }))
    .sort((a, b) => b.likes - a.likes)
    .slice(0, n)
}
