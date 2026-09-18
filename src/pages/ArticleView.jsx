import { Link, useParams } from 'react-router-dom'
import { useDoc } from '../hooks/useCollection'
import { useAuth } from '../context/AuthContext'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import { fmtDate } from '../lib/academicCalendar'

export default function ArticleView() {
  const { articleId } = useParams()
  const { row: article, loading, error } = useDoc('articles', articleId)
  const { user, isAdmin } = useAuth()

  if (loading) return <SkeletonList rows={2} />
  if (error) return <DataError what="articles" error={error} />
  if (!article) {
    return (
      <EmptyState
        title="Article not found"
        message="It may have been deleted."
        action={<Link to="/portal/articles" className="btn-secondary mt-2">Back to articles</Link>}
      />
    )
  }

  const canEdit = article.authorId === user.uid || isAdmin

  return (
    <article>
      <Link to="/portal/articles" className="mb-6 inline-block text-sm text-slate-500 hover:text-slate-800">← Articles</Link>

      <header className="mb-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip-brand">{article.category || 'General'}</span>
          {article.visibility === 'public' && <span className="chip bg-emerald-50 text-emerald-700">public</span>}
        </div>
        <h1 className="mt-3 page-title text-3xl">{article.title}</h1>
        <p className="page-subtitle">
          {article.authorName} · {fmtDate(article.createdAt)}
        </p>
        {canEdit && (
          <div className="mt-4 flex gap-2">
            <Link to={`/portal/articles/${article.id}/edit`} className="btn-secondary">Edit</Link>
            {article.visibility === 'public' && (
              <a href={`/articles/${article.id}`} target="_blank" rel="noreferrer" className="btn-ghost">View public page ↗</a>
            )}
          </div>
        )}
      </header>

      <div className="card p-8">
        <div className="prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: article.content || '' }} />
      </div>
    </article>
  )
}
