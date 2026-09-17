import { useState } from 'react'
import { doc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { updateProfile } from 'firebase/auth'
import { db, auth } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { GRADES, gradeLabel } from '../lib/grades'
import { fmtDate } from '../lib/academicCalendar'

function ProfileForm({ profile }) {
  const { user } = useAuth()
  const toast = useToast()
  // Mounted with `key={profile.uid}` so the initializer runs once the profile
  // has loaded — no effect has to copy props into state.
  const [form, setForm] = useState({
    name: profile.name || '',
    school: profile.school || '',
    phone: profile.phone || '',
    grades: profile.grades || [],
    subjects: (profile.subjects || []).join(', '),
  })
  const [saving, setSaving] = useState(false)

  const toggleGrade = (grade) =>
    setForm((current) => ({
      ...current,
      grades: current.grades.includes(grade) ? current.grades.filter((g) => g !== grade) : [...current.grades, grade],
    }))

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      // Status and role are intentionally absent — the rules reject changes to them.
      await updateDoc(doc(db, 'users', user.uid), {
        name: form.name.trim(),
        school: form.school.trim(),
        phone: form.phone.trim(),
        grades: form.grades,
        subjects: form.subjects.split(',').map((s) => s.trim()).filter(Boolean),
        updatedAt: serverTimestamp(),
      })
      if (form.name.trim() && form.name.trim() !== user.displayName) {
        await updateProfile(auth.currentUser, { displayName: form.name.trim() })
      }
      toast.success('Profile updated')
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <form onSubmit={save} className="card space-y-4 p-6">
          <div>
            <label className="label-caps" htmlFor="pf-name">Full name</label>
            <input id="pf-name" required className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label-caps" htmlFor="pf-school">School</label>
              <input id="pf-school" className="input" value={form.school} onChange={(e) => setForm({ ...form, school: e.target.value })} />
            </div>
            <div>
              <label className="label-caps" htmlFor="pf-phone">Phone (optional)</label>
              <input id="pf-phone" className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="label-caps" htmlFor="pf-subjects">Subjects you teach</label>
            <input id="pf-subjects" className="input" placeholder="Comma separated" value={form.subjects} onChange={(e) => setForm({ ...form, subjects: e.target.value })} />
          </div>
          <fieldset>
            <legend className="label-caps">Grades you teach</legend>
            <div className="flex flex-wrap gap-2">
              {GRADES.map((grade) => (
                <button
                  key={grade}
                  type="button"
                  aria-pressed={form.grades.includes(grade)}
                  onClick={() => toggleGrade(grade)}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold ${form.grades.includes(grade) ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                >
                  {gradeLabel(grade)}
                </button>
              ))}
            </div>
          </fieldset>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
          </div>
        </form>

        <aside className="card p-6">
          <p className="section-heading">Account</p>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <dt className="text-slate-500">Email</dt>
              <dd className="font-medium text-slate-800">{profile.email || user?.email}</dd>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <dt className="text-slate-500">Status</dt>
              <dd>
                <span className={`chip ${profile.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : profile?.status === 'suspended' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                  {profile.status || 'pending'}
                </span>
              </dd>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <dt className="text-slate-500">Role</dt>
              <dd className="font-medium text-slate-800">{profile.role || 'member'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Member since</dt>
              <dd className="font-medium text-slate-800">{fmtDate(profile.createdAt)}</dd>
            </div>
          </dl>
          <p className="card-meta mt-4">
            Approval and roles are changed by an administrator — ask in the feed if something looks wrong.
          </p>
      </aside>
    </div>
  )
}

export default function Profile() {
  const { profile } = useAuth()

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">My profile</h1>
        <p className="page-subtitle">Your school and classes help colleagues find the right resources and you.</p>
      </header>

      {!profile ? (
        <div className="card h-64 animate-pulse" />
      ) : (
        <ProfileForm key={profile.uid} profile={profile} />
      )}
    </div>
  )
}
