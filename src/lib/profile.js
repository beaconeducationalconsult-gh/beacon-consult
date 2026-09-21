/*
 * The member's own profile document.
 *
 * `firestore.rules` allows a signed-in user to create **their own**
 * `users/{uid}`, on one condition: `status` is exactly `'pending'` and `role` is
 * exactly `'member'`. That constraint is the whole point — a client that could
 * write its own `status:'approved'` would walk past every other rule — and it is
 * why the document's shape lives here rather than inline in a page: two screens
 * write it (sign-up, and the recovery screen for an account whose write failed),
 * and both must write the same thing.
 *
 * The recovery case is real, not theoretical. Sign up before the rules are
 * published and the Auth account is created while the profile write is refused,
 * which leaves a signed-in user the portal shows as "awaiting approval" with
 * nothing in the database for an administrator to approve.
 */

import { doc, serverTimestamp, setDoc } from 'firebase/firestore'
import { db } from '../firebase'

/** The values the rules require from a self-created profile. Not configurable. */
export const SELF_SIGNUP_STATUS = 'pending'
export const SELF_SIGNUP_ROLE = 'member'

/** A readable fallback name when the form (or Auth) has none. */
function fallbackName(user) {
  const email = String(user?.email || '').trim()
  if (email) return email.split('@')[0]
  return 'Member'
}

/**
 * The document, without Firestore — so the shape can be tested, and so the test
 * can assert the two fields the rules pin.
 */
export function ownProfileDoc(user, { name, school = '', grades = [], email, phone = '' } = {}) {
  return {
    name: String(name ?? user?.displayName ?? '').trim() || fallbackName(user),
    email: String(email ?? user?.email ?? '').trim(),
    school: String(school || '').trim(),
    grades: Array.isArray(grades) ? grades : [],
    phone: String(phone || '').trim(),
    status: SELF_SIGNUP_STATUS,
    role: SELF_SIGNUP_ROLE,
  }
}

/**
 * Write the profile for `user`, pending approval.
 *
 * `setDoc` (not `addDoc`) because the uid **is** the document id: the rules
 * check `request.auth.uid == uid`, so any other id would be refused.
 */
export async function createOwnProfile(user, fields = {}) {
  if (!user?.uid) throw new Error('Sign in first — a membership belongs to an account.')
  const record = ownProfileDoc(user, fields)
  await setDoc(doc(db, 'users', user.uid), { ...record, createdAt: serverTimestamp() })
  return record
}
