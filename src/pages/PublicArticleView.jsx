import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { doc, getDoc } from 'firebase/firestore'
import { db } from '../firebase'
import Navbar from '../components/Navbar'
import EmptyState from '../components/EmptyState'
import { fmtDate } from '../lib/academicCalendar'

export default function PublicArticleView() {
  const { articleId } = useParams()
  const [state, setState] = useState({ loading: true, article: null })

  useEffect(() => {
    let active = true
    getDoc(doc(db, 'articles', articleId))
      .then((snap) => active && setState({ loading: false, article: snap.exists() ? { id: snap.id, ...snap.data() } : null }))
      .catch(() => active && setState({ loading: false, article: null }))
    return () => {
      active = false
    }
  }, [articleId])

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-12">
        {state.loading && <div className="card h-64 animate-pulse" />}
        {!state.loading && !state.article && (
          <EmptyState
            title="Article not found"
            message="It may have been made private or removed."
            action={<Link to="/articles" className="btn-secondary mt-2">Back to articles</Link>}
          />
        )}
        {state.article && (
          <article className="card p-8">
            <h1 className="font-display text-3xl font-bold text-slate-900">{state.article.title}</h1>
            <p className="card-meta mt-3">
              {state.article.authorName || 'Beacon member'} ·{' '}
              {fmtDate(state.article.createdAt)}
            </p>
            <div
              className="prose prose-slate mt-6 max-w-none"
              // Content is authored by approved members through the Tiptap editor.
              dangerouslySetInnerHTML={{ __html: state.article.content || '' }}
            />
          </article>
        )}
      </main>
    </div>
  )
}
