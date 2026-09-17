import { useAuth } from '../context/AuthContext'

/** Shown by ProtectedLayout to signed-in members who are not (yet) approved. */
export default function PendingApproval({ suspended = false }) {
  const { profile, logout } = useAuth()

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 text-center">
      <div className="card p-8">
        <div
          className={`mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full ${
            suspended ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
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
          <div className="flex justify-between border-b border-slate-100 py-2">
            <dt className="text-slate-500">Name</dt>
            <dd className="font-medium text-slate-800">{profile?.name || '—'}</dd>
          </div>
          <div className="flex justify-between border-b border-slate-100 py-2">
            <dt className="text-slate-500">School</dt>
            <dd className="font-medium text-slate-800">{profile?.school || '—'}</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-slate-500">Status</dt>
            <dd className="font-medium text-slate-800">{profile?.status || 'pending'}</dd>
          </div>
        </dl>

        <button type="button" className="btn-secondary mt-6" onClick={logout}>
          Sign out
        </button>
      </div>
    </div>
  )
}
