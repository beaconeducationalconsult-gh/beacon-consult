import { useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteDoc, doc } from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useCollection } from '../hooks/useCollection'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import NotesTabs from '../components/NotesTabs'
import { PageHeader } from '../ui'
import { fmtDate } from '../lib/academicCalendar'

export default function Articles() {
  const { user, isAdmin } = useAuth()
  const toast = useToast()
  const [scope, setScope] = useState('all')
  const { rows, loading, error } = useCollection('articles', { max: 60, ordered: true })
  const [pendingDelete, setPendingDelete] = useState(null)

  const visible = scope === 'mine' ? rows.filter((a) => a.authorId === user.uid) : rows

  const remove = async () => {
    try {
      await deleteDoc(doc(db, 'articles', pendingDelete.id))
      toast.success('Article deleted')
    } catch (error) {
      toast.error(`Could not delete: ${error?.code || error.message}`)
    } finally {
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Articles"
        subtitle="Longer pieces on teaching practice. Public articles appear on the website."
        actions={<Link to="/portal/articles/new" className="btn-primary">New article</Link>}
      />

      <NotesTabs
        tabs={[
          { value: 'all', label: 'All', count: rows.length },
          { value: 'mine', label: 'Mine', count: rows.filter((a) => a.authorId === user.uid).length },
        ]}
        active={scope}
        onChange={setScope}
      />

      {error && <DataError what="articles" error={error} />}
{loading && <SkeletonList rows={3} />}
      {!loading && !error && visible.length === 0 && (
        <EmptyState
          title={scope === 'mine' ? 'You have not written an article yet' : 'No articles yet'}
          message="Articles are longer, edited pieces — different from feed posts."
          action={<Link to="/portal/articles/new" className="btn-primary mt-2">Write one</Link>}
        />
      )}

      <ul className="space-y-3">
        {visible.map((article) => (
          <li key={article.id} className="card card-hover p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <Link to={`/portal/articles/${article.id}`} className="card-title text-lg hover:underline">{article.title}</Link>
                <p className="card-meta mt-1">
                  {article.authorName} · {fmtDate(article.createdAt)}
                  {article.visibility === 'public' && ' · public'}
                </p>
                {article.excerpt && <p className="mt-2 line-clamp-2 text-sm text-text">{article.excerpt}</p>}
              </div>
              {(article.authorId === user.uid || isAdmin) && (
                <div className="flex shrink-0 gap-2">
                  <Link to={`/portal/articles/${article.id}/edit`} className="btn-secondary px-3 py-1.5 text-xs">Edit</Link>
                  <button type="button" className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setPendingDelete(article)}>Delete</button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>

      <ConfirmModal
        open={Boolean(pendingDelete)}
        title="Delete this article?"
        message="This cannot be undone."
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
