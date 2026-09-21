import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { signInWithEmailAndPassword } from 'firebase/auth'
import { auth } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import Navbar from '../components/Navbar'
import { authMessage } from '../lib/authError'

export default function Login() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [form, setForm] = useState({ email: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (!loading && user) return <Navigate to="/portal" replace />

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signInWithEmailAndPassword(auth, form.email.trim(), form.password)
      toast.success('Welcome back')
      navigate('/portal')
    } catch (err) {
      // The copy lives in src/lib/authError.js: a project that has not enabled
      // Email/Password, or has not authorized this domain, produces codes whose
      // raw text names neither the cause nor the fix.
      setError(authMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />
      <main className="mx-auto max-w-md px-4 py-14">
        <h1 className="page-title">Sign in</h1>
        <p className="page-subtitle">Members of the Beacon network only.</p>

        <form onSubmit={submit} className="card mt-8 space-y-4 p-6">
          <div>
            <label className="label-caps" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              className="input"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              className="input"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>

          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="text-center text-sm text-slate-500">
            No account yet?{' '}
            <Link to="/signup" className="link">
              Request access
            </Link>
          </p>
        </form>
      </main>
    </div>
  )
}
