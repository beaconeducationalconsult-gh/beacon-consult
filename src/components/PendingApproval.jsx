import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { authMessage } from '../lib/authError'
import { createOwnProfile } from '../lib/profile'

/**
 * Shown by ProtectedLayout to signed-in members who are not (yet) approved.
 *
 * Three cases, and the third one matters:
 *
 *   pending    the ordinary path — sign up, wait for an administrator
 *   suspended  an administrator closed the account
 *   **no row** `profile === null`: signed in, but there is no `users/{uid}`
 *              document at all. The screen used to show this as "Awaiting
 *              approval" with a row of dashes, which is a dead end — an
 *              administrator cannot approve a document that does not exist, and
 *              nothing on the page says what happened.
 *
 * How a member gets there: signing up **before** `firestore.rules` is published.
 * The Auth account is created and the profile write is refused, so the account
 * exists with no membership. The rules allow the member to create their own row
 * with `status:'pending'`/`role:'member'` (`src/lib/profile.js`), so the page can
 * offer exactly that instead of sending them to an administrator who has nothing
 * to click.
 */
export default function PendingApproval({ suspended = false }) {
  const { user, profile, logout } = useAuth()
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const missingProfile = !profile && Boolean(user)

  const finishSetup = async () => {
    setBusy(true)
    setError(null)
    try {
      await createOwnProfile(user)
      toast.success('Membership recorded — an administrator will review it shortly.')
    } catch (err) {
      setError(authMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (missingProfile) {
    return (
      <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 text-center">
        <div className="card p-8">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-warning-500">
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v5M12 16h.01" strokeLinecap="round" />
            </svg>
          </div>

          <h1 className="page-title">Finish setting up your account</h1>
          <p className="page-subtitle mt-2">
            You are signed in as <strong>{user?.email}</strong>, but the network has no membership
            record for this account yet — so there is nothing for an administrator to approve.
            This happens when an account is created before the database rules are published.
          </p>

          <p className="card-meta mt-4">
            Press the button and your record is created as <em>pending</em>, exactly as a fresh
            sign-up would: an administrator then reviews it as usual.
          </p>

          {error && <p className="mt-4 text-sm text-danger-600 dark:text-danger-500">{error}</p>}

          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            <button type="button" className="btn-primary" disabled={busy} onClick={finishSetup}>
              {busy ? 'Creating…' : 'Create my membership record'}
            </button>
            <button type="button" className="btn-secondary" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 text-center">
      <div className="card p-8">
        <div
          className={`mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full ${
            suspended ? 'bg-danger-50 text-danger-600 dark:bg-danger-500/15 dark:text-danger-500' : 'bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-warning-500'
          }`}
        >
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v5M12 16h.01" strokeLinecap="round" />
          </svg>
        </div>

        <h1 className="page-title">{suspended ? 'Account suspended' : 'Awaiting approval'}</h1>
        <p className="page-subtitle mt-2">
          {suspended
            ? 'Your access has been suspended. Contact a Beacon administrator if you think this is a mistake.'
            : 'Thanks for signing up. An administrator reviews new members — you will be able to open the portal as soon as your account is approved.'}
        </p>

        <dl className="mt-6 space-y-1 text-left text-sm">
          <div className="flex justify-between border-b border-line py-2">
            <dt className="text-muted">Name</dt>
            <dd className="font-medium text-heading">{profile?.name || '—'}</dd>
          </div>
          <div className="flex justify-between border-b border-line py-2">
            <dt className="text-muted">School</dt>
            <dd className="font-medium text-heading">{profile?.school || '—'}</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-muted">Status</dt>
            <dd className="font-medium text-heading">{profile?.status || 'pending'}</dd>
          </div>
        </dl>

        <button type="button" className="btn-secondary mt-6" onClick={logout}>
          Sign out
        </button>
      </div>
    </div>
  )
}
