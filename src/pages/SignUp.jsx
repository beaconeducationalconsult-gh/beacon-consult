import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createUserWithEmailAndPassword, updateProfile } from 'firebase/auth'
import { auth } from '../firebase'
import { authMessage } from '../lib/authError'
import { createOwnProfile } from '../lib/profile'
import { useToast } from '../context/ToastContext'
import { GRADES, gradeLabel } from '../lib/grades'

export default function SignUp() {
  const navigate = useNavigate()
  const toast = useToast()
  const [form, setForm] = useState({ name: '', email: '', school: '', grades: [], password: '', confirm: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const toggleGrade = (grade) =>
    setForm((current) => ({
      ...current,
      grades: current.grades.includes(grade)
        ? current.grades.filter((g) => g !== grade)
        : [...current.grades, grade],
    }))

  const submit = async (event) => {
    event.preventDefault()
    setError(null)

    if (form.password.length < 8) return setError('Choose a password with at least 8 characters.')
    if (form.password !== form.confirm) return setError('The two passwords do not match.')

    setBusy(true)
    try {
      const credential = await createUserWithEmailAndPassword(auth, form.email.trim(), form.password)
      await updateProfile(credential.user, { displayName: form.name.trim() })

      // The profile doc is the authorization source of truth, and the rules force
      // `status: 'pending'` / `role: 'member'` — see src/lib/profile.js.
      await createOwnProfile(credential.user, {
        name: form.name.trim(),
        school: form.school.trim(),
        grades: form.grades,
        email: form.email.trim(),
      })

      toast.success('Account created — an administrator will review it shortly.')
      navigate('/portal')
    } catch (err) {
      // A refused profile write (rules not published yet, or a suspended account)
      // lands here with `permission-denied`, and the account itself does exist —
      // so the message says both things instead of looking like a failed sign-up.
      setError(authMessage(err))
      if (err.code === 'permission-denied') {
        toast.error('Signed in, but your membership could not be saved. See the message below.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <main className="mx-auto max-w-xl px-4 py-14">
        <h1 className="page-title">Request access</h1>
        <p className="page-subtitle">
          Beacon is a members-only network of Ghanaian teachers. Tell us who you are and an
          administrator will approve your account.
        </p>

        <form onSubmit={submit} className="card mt-8 space-y-4 p-6">
          <div>
            <label className="label-caps" htmlFor="name">Full name</label>
            <input id="name" required className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="school">School</label>
            <input id="school" required className="input" value={form.school} onChange={(e) => setForm({ ...form, school: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="signup-email">Email</label>
            <input id="signup-email" type="email" autoComplete="email" required className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
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
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                    form.grades.includes(grade) ? 'bg-brand-600 text-white' : 'bg-surface-2 text-muted hover:bg-line'
                  }`}
                >
                  {gradeLabel(grade)}
                </button>
              ))}
            </div>
          </fieldset>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label-caps" htmlFor="signup-password">Password</label>
              <input id="signup-password" type="password" autoComplete="new-password" required className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
            <div>
              <label className="label-caps" htmlFor="confirm">Confirm password</label>
              <input id="confirm" type="password" autoComplete="new-password" required className="input" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
            </div>
          </div>

          {error && <p className="rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-700 dark:bg-danger-500/15 dark:text-danger-500">{error}</p>}

          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? 'Creating account…' : 'Create account'}
          </button>

          <p className="text-center text-sm text-muted">
            Already a member?{' '}
            <Link to="/login" className="link">
              Sign in
            </Link>
          </p>
        </form>
      </main>
    </div>
  )
}
