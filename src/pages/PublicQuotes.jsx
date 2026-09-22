import { useMemo, useState } from 'react'
import { useQuotes, useTheories, useQuoteLikes, quoteOfTheDay, theoryOfTheWeek } from '../hooks/useWisdom'

/** Public: static quotes JSON. No auth, works offline. */
export default function PublicQuotes() {
  const { data: quotes, loading } = useQuotes()
  const { data: theories } = useTheories()
  const likes = useQuoteLikes()
  const [tag, setTag] = useState(null)

  const daily = useMemo(() => quoteOfTheDay(quotes), [quotes])
  const weekly = useMemo(() => theoryOfTheWeek(theories), [theories])
  const tags = useMemo(() => [...new Set(quotes.flatMap((q) => q.tags || []))].sort(), [quotes])
  const visible = tag ? quotes.filter((q) => (q.tags || []).includes(tag)) : quotes

  return (
    <div>
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="page-title">Quote of the day</h1>
        <p className="page-subtitle">A daily quote or Ghanaian proverb, and a teaching theory each week.</p>

        {loading ? (
          <div className="card mt-8 h-40 animate-pulse" />
        ) : (
          <>
            {daily && (
              <blockquote className="card mt-8 border-l-4 border-l-accent-500 p-8">
                <p className="font-display text-2xl leading-snug text-heading">“{daily.text}”</p>
                <footer className="mt-4 text-sm text-muted">
                  — {daily.author}
                  {daily.meaning && <span className="mt-2 block italic text-text">{daily.meaning}</span>}
                </footer>
                <p className="card-meta mt-4">{likes[daily.id]?.count || 0} teachers like this</p>
              </blockquote>
            )}

            {weekly && (
              <section className="card mt-6 p-6">
                <p className="section-heading">Theory of the week</p>
                <h2 className="mt-2 font-display text-xl font-bold text-heading">{weekly.title}</h2>
                <p className="card-meta">{weekly.theorist}</p>
                <p className="mt-3 text-sm text-text">{weekly.definition}</p>
                <p className="mt-3 rounded-lg bg-accent-500/10 p-3 text-sm text-text">
                  <span className="font-semibold">In your classroom: </span>
                  {weekly.classroom}
                </p>
              </section>
            )}

            <div className="mt-10 flex flex-wrap gap-2">
              <button type="button" onClick={() => setTag(null)} className={!tag ? 'chip bg-brand-600 text-white' : 'chip hover:bg-surface-2'}>
                All
              </button>
              {tags.map((t) => (
                <button key={t} type="button" onClick={() => setTag(t)} className={tag === t ? 'chip bg-brand-600 text-white' : 'chip hover:bg-surface-2'}>
                  {t}
                </button>
              ))}
            </div>

            <ul className="mt-4 space-y-3">
              {visible.map((quote) => (
                <li key={quote.id} className="card p-5">
                  <p className="text-text">“{quote.text}”</p>
                  <p className="card-meta mt-2">
                    — {quote.author} · {likes[quote.id]?.count || 0} likes
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
      </main>
    </div>
  )
}
