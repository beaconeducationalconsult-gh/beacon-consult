import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { addDoc, collection, doc, getDoc, serverTimestamp, updateDoc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCurriculum } from '../hooks/useCurriculum'
import SubjectSelect from '../components/SubjectSelect'
import RichEditor from '../components/RichEditor'
import { GRADES, gradeLabel } from '../lib/grades'

const empty = { title: '', summary: '', grade: 'B1', subjectId: '', visibility: 'members', content: '' }

export default function NoteForm() {
  const { noteId } = useParams()
  const editing = Boolean(noteId)
  const { user, profile } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const { subjects, loading: loadingSubjects, error: subjectsError } = useCurriculum(form.grade)

  useEffect(() => {
    if (!editing) return
    getDoc(doc(db, 'notes', noteId))
      .then((snap) => {
        if (snap.exists()) {
          const { title, summary, grade, subjectId, visibility, content } = snap.data()
          setForm({ title: title || '', summary: summary || '', grade: grade || 'B1', subjectId: subjectId || '', visibility: visibility || 'members', content: content || '' })
        }
      })
      .finally(() => setLoading(false))
  }, [editing, noteId])

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    const payload = {
      ...form,
      // `visibility: 'private'` is what the rules enforce (author only). `status`
      // is the human word for the same choice, and is what a future
      // status-filtered list would read — it cannot gate reads today, because
      // notes written before it existed have no such field.
      status: form.visibility === 'private' ? 'draft' : 'published',
      subjectName: subjects.find((s) => s.id === form.subjectId)?.name || form.subjectId,
      updatedAt: serverTimestamp(),
    }
    try {
      if (editing) {
        await updateDoc(doc(db, 'notes', noteId), payload)
        toast.success('Note updated')
        navigate(`/portal/notes/${noteId}`)
      } else {
        const ref = await addDoc(collection(db, 'notes'), {
          ...payload,
          authorId: user.uid,
          authorName: profile?.name || 'Member',
          commentCount: 0,
          createdAt: serverTimestamp(),
        })
        toast.success('Note published')
        navigate(`/portal/notes/${ref.id}`)
      }
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
        <h1 className="page-title">{editing ? 'Edit note' : 'New study note'}</h1>
      </header>

      <div className="card mb-4 space-y-4 p-5">
        <div>
          <label className="label-caps" htmlFor="note-title">Title</label>
          <input id="note-title" required className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="label-caps" htmlFor="note-summary">Summary</label>
          <textarea id="note-summary" rows={2} maxLength={200} className="input" value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label-caps" htmlFor="note-grade">Grade</label>
            <select id="note-grade" className="input" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value, subjectId: '' })}>
              {GRADES.map((g) => <option key={g} value={g}>{gradeLabel(g)}</option>)}
            </select>
          </div>
          <div>
            <label className="label-caps" htmlFor="note-subject">Subject</label>
            <SubjectSelect
              id="note-subject"
              className="input"
              grade={form.grade}
              subjects={subjects}
              loading={loadingSubjects}
              error={subjectsError}
              value={form.subjectId}
              onChange={(e) => setForm({ ...form, subjectId: e.target.value })}
            />
          </div>
          <div>
            <label className="label-caps" htmlFor="note-visibility">Who can see it</label>
            <select id="note-visibility" className="input" value={form.visibility} onChange={(e) => setForm({ ...form, visibility: e.target.value })}>
              <option value="members">Members of the network</option>
              <option value="public">Public</option>
              <option value="private">Only me (draft)</option>
            </select>
          </div>
        </div>
      </div>

      <RichEditor value={form.content} onChange={(content) => setForm((f) => ({ ...f, content }))} placeholder="Write the note…" />

      <div className="mt-4 flex justify-end gap-3">
        <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Publish note'}</button>
      </div>
    </form>
  )
}
