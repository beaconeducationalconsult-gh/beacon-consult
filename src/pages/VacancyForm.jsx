import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { addDoc, collection, doc, getDoc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { GRADES, gradeLabel } from '../lib/grades'

const empty = {
  role: '',
  school: '',
  subject: '',
  grade: '',
  description: '',
  requirements: '',
  contact: '',
  deadline: '',
  status: 'draft',
}

export default function VacancyForm() {
  const { vacancyId } = useParams()
  const editing = Boolean(vacancyId)
  const { user, profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ ...empty, school: profile?.school || '' })
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!editing) return
    getDoc(doc(db, 'vacancies', vacancyId))
      .then((snap) => {
        if (snap.exists()) setForm({ ...empty, ...snap.data() })
      })
      .finally(() => setLoading(false))
  }, [editing, vacancyId])

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await updateDoc(doc(db, 'vacancies', vacancyId), { ...form, updatedAt: serverTimestamp() })
        toast.success('Vacancy updated')
      } else {
        await addDoc(collection(db, 'vacancies'), {
          ...form,
          authorId: user.uid,
          authorName: profile?.name || 'Member',
          createdAt: serverTimestamp(),
        })
        toast.success(form.status === 'published' ? 'Vacancy published' : 'Vacancy saved as draft')
      }
      navigate('/portal/vacancies')
    } catch (error) {
      toast.error(`Could not save: ${error?.code || error.message}`)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="card h-96 animate-pulse" />

  return (
    <form onSubmit={save}>
      <header className="mb-6">
        <h1 className="page-title">{editing ? 'Edit vacancy' : 'New vacancy'}</h1>
        <p className="page-subtitle">Published vacancies are readable by anyone — keep contact details professional.</p>
      </header>

      <div className="card space-y-4 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label-caps" htmlFor="role">Role</label>
            <input id="role" required className="input" placeholder="Class teacher — Basic 4" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="school">School</label>
            <input id="school" required className="input" value={form.school} onChange={(e) => setForm({ ...form, school: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="v-subject">Subject (optional)</label>
            <input id="v-subject" className="input" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="v-grade">Grade (optional)</label>
            <select id="v-grade" className="input" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })}>
              <option value="">Any</option>
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="label-caps" htmlFor="description">Description</label>
          <textarea id="description" rows={4} className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div>
          <label className="label-caps" htmlFor="requirements">Requirements</label>
          <textarea id="requirements" rows={3} className="input" value={form.requirements} onChange={(e) => setForm({ ...form, requirements: e.target.value })} />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label-caps" htmlFor="contact">How to apply</label>
            <input id="contact" className="input" placeholder="Email or phone" value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="deadline">Deadline</label>
            <input id="deadline" type="date" className="input" value={form.deadline || ''} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          </div>
          <div>
            <label className="label-caps" htmlFor="v-status">Status</label>
            <select id="v-status" className="input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="draft">Draft (members only)</option>
              <option value="published">Published (public)</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>
      </div>

      <div className="mt-4 flex justify-end gap-3">
        <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save vacancy'}</button>
      </div>
    </form>
  )
}
