import { createContext, useContext, useEffect, useState } from 'react'
import { onAuthStateChanged, signOut } from 'firebase/auth'
import { doc, onSnapshot } from 'firebase/firestore'
import { auth, db } from '../firebase'

const AuthContext = createContext(null)

/**
 * The single source of truth for "who am I / am I approved / am I admin".
 *
 * `profile` is deliberately tri-state:
 *   undefined → still loading
 *   null      → signed in but no users/{uid} document (rare; see docs/gotchas.md)
 *   object    → the live profile
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(undefined)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let unsubProfile = null

    const unsubAuth = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser)
      if (unsubProfile) unsubProfile()

      if (!nextUser) {
        setProfile(null)
        setLoading(false)
        return
      }

      setLoading(true)
      unsubProfile = onSnapshot(
        doc(db, 'users', nextUser.uid),
        (snap) => {
          setProfile(snap.exists() ? { uid: nextUser.uid, ...snap.data() } : null)
          setLoading(false)
        },
        (error) => {
          // A rules-denied profile read must not strand the user on a spinner.
          console.error('[beacon] profile subscription failed:', error?.code || error)
          setProfile(null)
          setLoading(false)
        }
      )
    })

    return () => {
      if (unsubProfile) unsubProfile()
      unsubAuth()
    }
  }, [])

  const isApproved = profile?.status === 'approved'
  const isAdmin = profile?.role === 'admin'
  const canUsePortal = isApproved || isAdmin

  const logout = () => signOut(auth)

  return (
    <AuthContext.Provider
      value={{ user, profile, loading, isApproved, isAdmin, canUsePortal, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// Provider and consumer hook live together on purpose: they are one API.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
