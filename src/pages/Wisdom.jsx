import { useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useQuotes, useTheories, useQuoteLikes, toggleQuoteLike, quoteOfTheDay, theoryOfTheWeek } from '../hooks/useWisdom'

export default function Wisdom() {
  const { user } = useAuth()
  const toast = useToast()
  const { data: quotes } = useQuotes()
  const { data: theories } = useTheories()
  const likes = useQuoteLikes()
  const [tab, setTab] = useState('quotes')
  const [tag, setTag] = useState(null)

  const daily = useMemo(() => quoteOfTheDay(quotes), [quotes])
  const weekly = useMemo(() => theoryOfTheWeek(theories), [theories])
  const visible = tag ? quotes.filter((q) => (q.tags || []).includes(tag)) : quotes
  const tags = useMemo(() => [...new Set(quotes.flatMap((q) => q.tags || []))].sort(), [quotes])

  const like = async (quote) => {
    try {
      await toggleQuoteLike(quote.id, user.uid, likes)
    } catch (error) {
      toast.error(`Could not save your like: ${error?.code || error.message}`)
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="page-title">Wisdom</h1>
        <p className="page-subtitle">A quote or proverb each day, and a classroom theory each week.</p>
      </header>

      {daily && (
        <blockquote className="card border-l-4 border-l-accent-500 p-8">
          <p className="section-heading">Today</p>
          <p className="mt-2 font-display text-2xl leading-snug text-slate-900">“{daily.text}”</p>
          <footer className="mt-4 text-sm text-slate-500">
            — {daily.author}
            {daily.meaning && <span className="mt-2 block italic text-slate-600">{daily.meaning}</span>}
          </footer>
          <button
            type="button"
            onClick={() => like(daily)}
            aria-pressed={Boolean(likes[daily.id]?.likedBy?.includes(user.uid))}
            className={`mt-5 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${
              likes[daily.id]?.likedBy?.includes(user.uid) ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            ♥ {likes[daily.id]?.count || 0}
          </button>
        </blockquote>
      )}

      <div className="mt-8 flex gap-1 border-b border-slate-200" role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'quotes'} onClick={() => setTab('quotes')} className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold ${tab === 'quotes' ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500'}`}>
          Quotes & proverbs
        </button>
        <button type="button" role="tab" aria-selected={tab === 'theories'} onClick={() => setTab('theories')} className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold ${tab === 'theories' ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500'}`}>
          Teaching theories
        </button>
      </div>

      {tab === 'quotes' ? (
        <>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={() => setTag(null)} className={`chip ${!tag ? 'bg-brand-600 text-white' : 'hover:bg-slate-200'}`}>All</button>
            {tags.map((t) => (
              <button key={t} type="button" onClick={() => setTag(t)} className={`chip ${tag === t ? 'bg-brand-600 text-white' : 'hover:bg-slate-200'}`}>{t}</button>
            ))}
          </div>
          <ul className="mt-4 space-y-3">
            {visible.map((quote) => {
              const liked = Boolean(likes[quote.id]?.likedBy?.includes(user.uid))
              return (
                <li key={quote.id} className="card flex items-start justify-between gap-4 p-5">
                  <div className="min-w-0">
                    <p className="text-slate-800">“{quote.text}”</p>
                    <p className="card-meta mt-2">— {quote.author}</p>
                    {quote.meaning && <p className="card-meta mt-1 italic">{quote.meaning}</p>}
                  </div>
                  <button
                    type="button"
                    onClick={() => like(quote)}
                    aria-pressed={liked}
                    className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${liked ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                  >
                    ♥ {likes[quote.id]?.count || 0}
                  </button>
                </li>
              )
            })}
          </ul>
        </>
      ) : (
        <ul className="mt-4 space-y-3">
          {weekly && (
            <li className="card border-l-4 border-l-brand-500 p-5">
              <p className="section-heading">This week</p>
              <h2 className="mt-1 card-title text-lg">{weekly.title}</h2>
              <p className="card-meta">{weekly.theorist}</p>
              <p className="mt-2 text-sm text-slate-600">{weekly.definition}</p>
            </li>
          )}
          {theories.map((theory) => (
            <li key={theory.id} className="card p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="card-title">{theory.title}</h2>
                <span className="chip">{theory.category}</span>
              </div>
              <p className="card-meta mt-1">{theory.theorist}</p>
              <p className="mt-3 text-sm text-slate-600">{theory.definition}</p>
              <p className="mt-3 rounded-lg bg-accent-500/10 p-3 text-sm text-slate-700">
                <span className="font-semibold">In your classroom: </span>
                {theory.classroom}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
