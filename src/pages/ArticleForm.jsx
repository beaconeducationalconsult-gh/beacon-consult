import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { addDoc, collection, doc, getDoc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import RichEditor from '../components/RichEditor'

const empty = { title: '', excerpt: '', category: 'Teaching practice', visibility: 'members', content: '' }

export default function ArticleForm() {
  const { articleId } = useParams()
  const editing = Boolean(articleId)
  const { user, profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!editing) return
    getDoc(doc(db, 'articles', articleId))
      .then((snap) => {
        if (snap.exists()) {
          const { title, excerpt, category, visibility, content } = snap.data()
          setForm({ title: title || '', excerpt: excerpt || '', category: category || '', visibility: visibility || 'members', content: content || '' })
        }
      })
      .finally(() => setLoading(false))
  }, [articleId, editing])

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await updateDoc(doc(db, 'articles', articleId), { ...form, updatedAt: serverTimestamp() })
        toast.success('Article updated')
      } else {
        const ref = await addDoc(collection(db, 'articles'), {
          ...form,
          authorId: user.uid,
          authorName: profile?.name || 'Member',
          likesCount: 0,
          likedBy: [],
          createdAt: serverTimestamp(),
        })
        toast.success('Article published')
        navigate(`/portal/articles/${ref.id}`)
        return
      }
      navigate(`/portal/articles/${articleId}`)
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
        <h1 className="page-title">{editing ? 'Edit article' : 'New article'}</h1>
        <p className="page-subtitle">Public articles are readable by anyone on the website.</p>
      </header>

      <div className="card mb-4 space-y-4 p-5">
        <div>
          <label className="label-caps" htmlFor="title">Title</label>
          <input id="title" required className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="label-caps" htmlFor="excerpt">Summary</label>
          <textarea id="excerpt" rows={2} maxLength={250} className="input" value={form.excerpt} onChange={(e) => setForm({ ...form, excerpt: e.target.value })} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label-caps" htmlFor="category">Category</label>
            <select id="category" className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {['Teaching practice', 'Assessment', 'Curriculum', 'Classroom management', 'Leadership', 'News'].map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="visibility">Who can read it</label>
            <select id="visibility" className="input" value={form.visibility} onChange={(e) => setForm({ ...form, visibility: e.target.value })}>
              <option value="members">Members of the network</option>
              <option value="public">Public (on the website)</option>
            </select>
          </div>
        </div>
      </div>

      <RichEditor value={form.content} onChange={(content) => setForm((f) => ({ ...f, content }))} placeholder="Write your article…" />

      <div className="mt-4 flex justify-end gap-3">
        <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Publish'}</button>
      </div>
    </form>
  )
}
