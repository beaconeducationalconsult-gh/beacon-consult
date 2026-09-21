import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { collection, getDocs, query, where } from 'firebase/firestore'
import { db } from '../firebase'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { fmtDate } from '../lib/academicCalendar'

/** Public: `articles` where visibility == 'public'. */
export default function PublicArticles() {
  const [state, setState] = useState({ loading: true, articles: [], error: null })

  useEffect(() => {
    let active = true
    getDocs(query(collection(db, 'articles'), where('visibility', '==', 'public')))
      .then((snap) => {
        if (!active) return
        const articles = snap.docs
          .map((d) => ({ id: d.id, ...d.data() }))
          .sort((a, b) => (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0))
        setState({ loading: false, articles, error: null })
      })
      .catch((error) => active && setState({ loading: false, articles: [], error }))
    return () => {
      active = false
    }
  }, [])

  return (
    <div>
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="page-title">Articles</h1>
        <p className="page-subtitle">Teaching practice, written by members of the network.</p>

        <div className="mt-8 space-y-4">
          {state.loading && <SkeletonList rows={3} />}
          {!state.loading && (state.error || state.articles.length === 0) && (
            <EmptyState
              title={state.error ? 'Articles are unavailable' : 'No public articles yet'}
              message={state.error ? 'Please try again in a moment.' : 'Members publish articles from the portal — they appear here when set to public.'}
              action={<Link to="/login" className="btn-secondary mt-2">Sign in</Link>}
            />
          )}
          {state.articles.map((article) => (
            <article key={article.id} className="card card-hover p-6">
              <Link to={`/articles/${article.id}`} className="block">
                <h2 className="card-title text-lg">{article.title}</h2>
                {article.excerpt && <p className="mt-2 text-sm text-slate-600">{article.excerpt}</p>}
                <p className="card-meta mt-3">
                  {article.authorName || 'Beacon member'} · {fmtDate(article.createdAt)}
                  {article.category ? ` · ${article.category}` : ''}
                </p>
              </Link>
            </article>
          ))}
        </div>
      </main>
    </div>
  )
}
