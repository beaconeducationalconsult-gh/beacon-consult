import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  addDoc, arrayRemove, arrayUnion, collection, doc, getCountFromServer, increment,
  onSnapshot, query, serverTimestamp, updateDoc, where, limit,
} from 'firebase/firestore'
import { db } from '../firebase'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { SkeletonList } from '../components/Skeleton'
import EmptyState from '../components/EmptyState'
import { useQuotes, useQuoteLikes, quoteOfTheDay, topLikedQuotes } from '../hooks/useWisdom'
import { WEEKLY_QUOTA, isoWeekKey } from '../lib/week'
import { fmtDate, getAcademicStatus, termProgress, termWeek } from '../lib/academicCalendar'

function QuoteCard() {
  const { data: quotes } = useQuotes()
  const likes = useQuoteLikes()
  const quote = quoteOfTheDay(quotes)
  if (!quote) return null
  return (
    <div className="card border-l-4 border-l-accent-500 p-5">
      <p className="section-heading">Quote of the day</p>
      <p className="mt-2 font-display text-lg leading-snug text-slate-900">“{quote.text}”</p>
      <p className="card-meta mt-2">— {quote.author} · {likes[quote.id]?.count || 0} likes</p>
    </div>
  )
}

function TermProgressCard({ progress }) {
  const status = getAcademicStatus()
  if (status.state !== 'in-term') {
    return (
      <div className="card p-5">
        <p className="section-heading">School year</p>
        <p className="mt-2 text-sm text-slate-600">
          {status.state === 'before-term'
            ? `${status.term.label} begins in ${status.daysUntilStart} day(s).`
            : 'Between terms — enjoy the break.'}
        </p>
      </div>
    )
  }
  const pct = Math.round(termProgress(status.term) * 100)
  return (
    <div className="card p-5">
      <p className="section-heading">{status.term.label} progress</p>
      <p className="mt-2 text-sm text-slate-600">
        Week {termWeek(status.term) ?? '—'} of {status.term.weeks} · {status.daysRemaining} days left
      </p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
      {progress ? (
        <p className="card-meta mt-3">{progress.subjectWeeks ?? 0} subject-week(s) recorded this term</p>
      ) : (
        <Link to="/portal/progress" className="link mt-3 inline-block text-xs">Start tracking your progress →</Link>
      )}
    </div>
  )
}

function QuotaCard() {
  const { user } = useAuth()
  const [count, setCount] = useState(null)

  useEffect(() => {
    if (!user) return undefined
    let active = true
    // Server-side count — avoids downloading the whole bank just to show a number.
    getCountFromServer(
      query(collection(db, 'questions'), where('authorId', '==', user.uid), where('weekKey', '==', isoWeekKey()))
    )
      .then((snap) => active && setCount(snap.data().count))
      .catch(() => active && setCount(null))
    return () => {
      active = false
    }
  }, [user])

  return (
    <div className="card p-5">
      <p className="section-heading">This week's contributions</p>
      <p className="mt-2 text-sm text-slate-600">
        {count == null ? '—' : count} of {WEEKLY_QUOTA} questions added to the bank
      </p>
      <Link to="/portal/questions/new" className="btn-secondary mt-3 w-full text-xs">
        Add a question
      </Link>
    </div>
  )
}

function Leaderboard() {
  const { data: quotes } = useQuotes()
  const likes = useQuoteLikes()
  const top = topLikedQuotes(quotes, likes, 5).filter((q) => q.likes > 0)
  if (!top.length) return null
  return (
    <div className="card p-5">
      <p className="section-heading">Most-loved quotes</p>
      <ol className="mt-3 space-y-2">
        {top.map((quote, index) => (
          <li key={quote.id} className="flex gap-3 text-sm">
            <span className="font-mono text-xs text-slate-400">{index + 1}</span>
            <span className="min-w-0 flex-1">
              <span className="line-clamp-2 text-slate-700">“{quote.text}”</span>
              <span className="card-meta">— {quote.author} · {quote.likes} likes</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}

export default function Feed() {
  const { user, profile } = useAuth()
  const toast = useToast()
  const [posts, setPosts] = useState(null)
  const [content, setContent] = useState('')
  const [posting, setPosting] = useState(false)
  const [myProgress, setMyProgress] = useState(null)

  useEffect(() => {
    return onSnapshot(
      query(collection(db, 'posts'), limit(50)),
      (snap) => {
        const rows = snap.docs
          .map((d) => ({ id: d.id, ...d.data() }))
          .sort((a, b) => (b.timestamp?.seconds || 0) - (a.timestamp?.seconds || 0))
        setPosts(rows)
      },
      (error) => {
        // Error callback so a denied read degrades to an empty feed rather than
        // throwing (see docs/gotchas.md).
        console.warn('[beacon] feed unavailable:', error?.code || error)
        setPosts([])
      }
    )
  }, [])

  useEffect(() => {
    if (!user) return undefined
    return onSnapshot(
      doc(db, 'progress', user.uid),
      (snap) => setMyProgress(snap.exists() ? snap.data() : null),
      () => setMyProgress(null)
    )
  }, [user])

  const subjectWeeks = myProgress
    ? Object.values(myProgress.weeks || {}).reduce((sum, weeks) => sum + (Array.isArray(weeks) ? weeks.length : 0), 0)
    : 0

  const publish = async (event) => {
    event.preventDefault()
    if (!content.trim()) return
    setPosting(true)
    try {
      await addDoc(collection(db, 'posts'), {
        content: content.trim(),
        authorId: user.uid,
        authorName: profile?.name || 'Member',
        likesCount: 0,
        likedBy: [],
        timestamp: serverTimestamp(),
      })
      setContent('')
      toast.success('Posted to the feed')
    } catch (error) {
      toast.error(`Could not post: ${error?.code || error.message}`)
    } finally {
      setPosting(false)
    }
  }

  const toggleLike = async (post) => {
    const liked = (post.likedBy || []).includes(user.uid)
    try {
      await updateDoc(doc(db, 'posts', post.id), {
        likedBy: liked ? arrayRemove(user.uid) : arrayUnion(user.uid),
        likesCount: increment(liked ? -1 : 1),
      })
    } catch (error) {
      toast.error(`Could not save your like: ${error?.code || error.message}`)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <div>
        <header className="mb-6">
          <h1 className="page-title">Welcome back{profile?.name ? `, ${profile.name.split(' ')[0]}` : ''}</h1>
          <p className="page-subtitle">What teachers in the network are working on.</p>
        </header>

        <form onSubmit={publish} className="card mb-6 p-5">
          <label className="label-caps" htmlFor="post">Share with the network</label>
          <textarea
            id="post"
            rows={3}
            className="input resize-y"
            placeholder="A resource, a question, something that worked in your class…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="mt-3 flex justify-end">
            <button type="submit" className="btn-primary" disabled={posting || !content.trim()}>
              {posting ? 'Posting…' : 'Post'}
            </button>
          </div>
        </form>

        {posts === null && <SkeletonList rows={3} />}
        {posts?.length === 0 && (
          <EmptyState title="The feed is quiet" message="Be the first to share something with the network." />
        )}

        <ul className="space-y-4">
          {posts?.map((post) => {
            const liked = (post.likedBy || []).includes(user.uid)
            return (
              <li key={post.id} className="card p-5">
                <div className="flex items-start gap-3">
                  <Link to={`/portal/authors/${post.authorId}`} className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-600 text-sm font-bold text-white">
                    {(post.authorName || '?').slice(0, 1).toUpperCase()}
                  </Link>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm">
                      <Link to={`/portal/authors/${post.authorId}`} className="font-semibold text-slate-800 hover:underline">
                        {post.authorName || 'Member'}
                      </Link>
                      <span className="card-meta ml-2">{fmtDate(post.timestamp)}</span>
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{post.content}</p>

                    <div className="mt-3 flex items-center gap-4">
                      <button
                        type="button"
                        onClick={() => toggleLike(post)}
                        aria-pressed={liked}
                        className={`inline-flex items-center gap-1.5 text-xs font-semibold ${liked ? 'text-brand-700' : 'text-slate-500 hover:text-slate-800'}`}
                      >
                        <svg viewBox="0 0 24 24" className="h-4 w-4" fill={liked ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.75">
                          <path d="M7 10v10H4V10h3Zm3 10V9.5L13 4l.7.4a2 2 0 0 1 .9 2.3L14 9h4.2a2 2 0 0 1 1.9 2.6l-1.6 6A2 2 0 0 1 16.6 20H10Z" />
                        </svg>
                        {post.likesCount || 0}
                      </button>
                      <Link to={`/portal/authors/${post.authorId}`} className="text-xs font-semibold text-slate-500 hover:text-slate-800">
                        View author
                      </Link>
                    </div>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      </div>

      <aside className="space-y-4">
        <QuoteCard />
        <TermProgressCard progress={{ subjectWeeks }} />
        <QuotaCard />
        <Leaderboard />
      </aside>
    </div>
  )
}
