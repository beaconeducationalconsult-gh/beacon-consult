import { useState } from 'react'
import { doc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import NotesTabs from '../components/NotesTabs'
import ConfirmModal from '../components/ConfirmModal'
import { fmtDate } from '../lib/academicCalendar'

const STATUSES = [
  ['pending', 'Pending', 'bg-amber-50 text-amber-700'],
  ['approved', 'Approved', 'bg-emerald-50 text-emerald-700'],
  ['suspended', 'Suspended', 'bg-red-50 text-red-700'],
]

/** Admin only — ProtectedLayout redirects members away from the role gate. */
export default function Members() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('pending')
  const { rows, loading } = useCollection('users', { max: 200, sort: 'createdAt' })
  const [pendingAction, setPendingAction] = useState(null)

  if (!isAdmin) {
    return <EmptyState title="Administrators only" message="This page manages member accounts." />
  }

  const visible = scope === 'all' ? rows : rows.filter((member) => (member.status || 'pending') === scope)

  const apply = async () => {
    const { member, status } = pendingAction
    try {
      await updateDoc(doc(db, 'users', member.id), { status, updatedAt: serverTimestamp() })
      toast.success(`${member.name || 'Member'} is now ${status}`)
    } catch (error) {
      toast.error(`Could not update: ${error?.code || error.message}`)
    } finally {
      setPendingAction(null)
    }
  }

  const setRole = async (member, role) => {
    try {
      await updateDoc(doc(db, 'users', member.id), { role, updatedAt: serverTimestamp() })
      toast.success(`${member.name || 'Member'} is now ${role === 'admin' ? 'an administrator' : 'a member'}`)
    } catch (error) {
      toast.error(`Could not change the role: ${error?.code || error.message}`)
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Members</h1>
        <p className="page-subtitle">Approve new teachers, suspend access and manage administrator roles.</p>
      </header>

      <NotesTabs
        tabs={[
          { value: 'pending', label: 'Pending', count: rows.filter((m) => (m.status || 'pending') === 'pending').length },
          { value: 'approved', label: 'Approved', count: rows.filter((m) => m.status === 'approved').length },
          { value: 'suspended', label: 'Suspended', count: rows.filter((m) => m.status === 'suspended').length },
          { value: 'all', label: 'All', count: rows.length },
        ]}
        active={scope}
        onChange={setScope}
      />

      {loading && <SkeletonList rows={4} />}
      {!loading && visible.length === 0 && (
        <EmptyState title="Nothing to review" message="New sign-ups appear here for approval." />
      )}

      <ul className="space-y-3">
        {visible.map((member) => (
          <li key={member.id} className="card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="card-title">
                  {member.name || 'Unnamed member'}
                  {member.role === 'admin' && <span className="chip bg-amber-50 text-amber-700 ml-2">admin</span>}
                </p>
                <p className="card-meta">{member.email} · {member.school || 'school not given'}</p>
                <p className="card-meta mt-1">
                  {(member.grades || []).map((g) => g).join(', ') || 'no grades listed'} · joined{' '}
                  {fmtDate(member.createdAt)}
                </p>
              </div>
              <span className={`chip ${(STATUSES.find(([value]) => value === (member.status || 'pending')) || [])[2]}`}>
                {member.status || 'pending'}
              </span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {member.status !== 'approved' && (
                <button type="button" className="btn-primary px-3 py-1.5 text-xs" onClick={() => setPendingAction({ member, status: 'approved' })}>
                  Approve
                </button>
              )}
              {member.status !== 'suspended' && member.id !== user.uid && (
                <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={() => setPendingAction({ member, status: 'suspended' })}>
                  Suspend
                </button>
              )}
              {member.status === 'suspended' && (
                <button type="button" className="btn-secondary px-3 py-1.5 text-xs" onClick={() => setPendingAction({ member, status: 'pending' })}>
                  Return to pending
                </button>
              )}
              {member.id !== user.uid && (
                <button
                  type="button"
                  className="btn-ghost px-3 py-1.5 text-xs"
                  onClick={() => setRole(member, member.role === 'admin' ? 'member' : 'admin')}
                >
                  {member.role === 'admin' ? 'Revoke admin' : 'Make admin'}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <ConfirmModal
        open={Boolean(pendingAction)}
        title={pendingAction?.status === 'approved' ? 'Approve this member?' : pendingAction?.status === 'suspended' ? 'Suspend this member?' : 'Return to pending?'}
        message={
          pendingAction?.status === 'approved'
            ? `${pendingAction?.member?.name} will be able to open the portal immediately.`
            : pendingAction?.status === 'suspended'
              ? `${pendingAction?.member?.name} will lose access to the portal until you approve them again.`
              : `${pendingAction?.member?.name} will return to the pending queue.`
        }
        confirmLabel={pendingAction?.status === 'approved' ? 'Approve' : pendingAction?.status === 'suspended' ? 'Suspend' : 'Return to pending'}
        tone={pendingAction?.status === 'suspended' ? 'danger' : 'primary'}
        onConfirm={apply}
        onCancel={() => setPendingAction(null)}
      />
    </div>
  )
}
