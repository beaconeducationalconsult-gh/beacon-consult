import { describe, expect, it, vi } from 'vitest'

/*
 * The two screens a new deployment meets first.
 *
 * Sign-in and sign-up used to fall through to Firebase's raw message, and the
 * failures a **fresh project** produces are the ones its text explains worst:
 * `auth/operation-not-allowed` (Email/Password provider not enabled) and
 * `auth/unauthorized-domain` (the deployed address is not on the allow-list)
 * both arrive as "Firebase: Error (auth/…)" with no hint that a console step is
 * missing. The person who meets them is also the person who can fix them, so the
 * message names the console path.
 *
 * The profile doc's shape is asserted here too, because `firestore.rules` pins
 * two of its fields and a page that forgets them gets `permission-denied` at
 * sign-up — the failure that produced the recovery screen in the first place.
 */

vi.mock('../firebase', () => ({ db: { _db: true } }))
vi.mock('firebase/firestore', () => ({
  doc: (_db, name, id) => ({ name, id }),
  serverTimestamp: () => 'SERVER_TIMESTAMP',
  setDoc: vi.fn(async () => {}),
}))

const { authMessage, isSetupError } = await import('./authError')
const { createOwnProfile, ownProfileDoc, SELF_SIGNUP_STATUS, SELF_SIGNUP_ROLE } = await import('./profile')

describe('auth failures say what to do', () => {
  it('names the console step for the failures a new project produces', () => {
    expect(authMessage({ code: 'auth/operation-not-allowed' }))
      .toMatch(/Authentication.*Sign-in method.*Email\/Password/)
    expect(authMessage({ code: 'auth/unauthorized-domain' }))
      .toMatch(/Authorized domains/)
    expect(authMessage({ code: 'auth/configuration-not-found' }))
      .toMatch(/Authentication.*Get started/)
    expect(authMessage({ code: 'auth/invalid-api-key' })).toContain('VITE_FIREBASE_')
  })

  it('says the account exists when only the profile write failed', () => {
    // The sign-up half-success: Auth created the account, Firestore refused the
    // membership row. Calling that "sign-up failed" sends people to the wrong place.
    const message = authMessage({ code: 'permission-denied' })
    expect(message).toContain('account was created')
    expect(message).toContain('firestore.rules')
  })

  it('keeps the ordinary wrong-password guidance human', () => {
    for (const code of ['auth/invalid-credential', 'auth/wrong-password', 'auth/invalid-login-credentials']) {
      expect(authMessage({ code })).toBe('That email and password do not match.')
    }
    expect(authMessage({ code: 'auth/user-not-found' })).toContain('Request access')
    expect(authMessage({ code: 'auth/email-already-in-use' })).toContain('signing in')
  })

  it('falls back to Firebase text rather than a generic apology', () => {
    // An unrecognised code must stay searchable — "something went wrong" hides the one
    // piece of information the person could act on.
    expect(authMessage({ code: 'auth/some-new-code', message: 'Firebase: foo (auth/some-new-code).' }))
      .toContain('auth/some-new-code')
    expect(authMessage({})).toContain('Try again')
  })

  it('separates "not configured" from "wrong password"', () => {
    expect(isSetupError({ code: 'auth/operation-not-allowed' })).toBe(true)
    expect(isSetupError({ code: 'permission-denied' })).toBe(true)
    expect(isSetupError({ code: 'auth/wrong-password' })).toBe(false)
    expect(isSetupError(undefined)).toBe(false)
  })
})

describe('the membership row a member may create for themselves', () => {
  it('writes exactly the status and role the rules allow', () => {
    const doc = ownProfileDoc({ uid: 'u1', email: 'ama@school.edu.gh', displayName: 'Ama Mensah' })
    expect(doc.status).toBe('pending')
    expect(doc.role).toBe('member')
    expect(SELF_SIGNUP_STATUS).toBe('pending')
    expect(SELF_SIGNUP_ROLE).toBe('member')
    // Firestore rejects `undefined`; every field here must be concrete.
    for (const [key, value] of Object.entries(doc)) {
      expect(value, `${key} must not be undefined`).toBeDefined()
    }
  })

  it('falls back to something readable when the form has no name', () => {
    expect(ownProfileDoc({ uid: 'u1', email: 'kofi@school.edu.gh' }).name).toBe('kofi')
    expect(ownProfileDoc({ uid: 'u1' }).name).toBe('Member')
    expect(ownProfileDoc({ uid: 'u1' }, { name: '  Esi  ' }).name).toBe('Esi')
    expect(ownProfileDoc({ uid: 'u1' }, { grades: 'B4' }).grades).toEqual([])
  })

  it('refuses to write anything without a signed-in account', async () => {
    // The recovery screen calls this after a page reload, and a signed-out tab is
    // one refresh away; the rules would refuse the write anyway, but the error
    // should name the real problem.
    await expect(createOwnProfile(null)).rejects.toThrow(/Sign in first/)
  })

  it('writes to users/{uid} — the only id the rules accept', async () => {
    const firestore = await import('firebase/firestore')
    await createOwnProfile({ uid: 'uid-42', email: 'a@b.c' }, { name: 'Ama', school: 'Beacon Basic' })
    expect(firestore.setDoc).toHaveBeenCalledTimes(1)
    const [reference, data] = firestore.setDoc.mock.calls[0]
    expect(reference).toEqual({ name: 'users', id: 'uid-42' })
    expect(data.status).toBe('pending')
    expect(data.role).toBe('member')
    expect(data.school).toBe('Beacon Basic')
    expect(data.createdAt).toBe('SERVER_TIMESTAMP')
  })
})
