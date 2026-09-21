/**
 * Footer for a paged list: "Load more" while older rows exist, nothing when
 * they do not.
 *
 * The point is that a capped list and an exhausted one stop looking alike. A
 * `limit(80)` query with no cursor is silent truncation — the page said "80
 * items" whether or not there were 400 more. `usePagedCollection` tracks
 * `hasMore` from the page size, and this renders that state honestly, including
 * the failure to fetch the next page.
 */
export default function LoadMore({ hasMore, loading, error, onLoad, loaded }) {
  if (!hasMore) {
    return loaded ? (
      <p className="mt-6 text-center text-xs text-slate-400">
        {loaded} shown — that is everything.
      </p>
    ) : null
  }

  return (
    <div className="mt-6 flex flex-col items-center gap-2">
      <button type="button" className="btn-secondary" onClick={onLoad} disabled={loading}>
        {loading ? 'Loading…' : 'Load more'}
      </button>
      <p className="text-xs text-slate-400">{loaded} shown</p>
      {error && (
        <p className="text-xs text-rose-700">
          More could not be loaded ({error.code || error.message || 'error'}). Refresh to try again.
        </p>
      )}
    </div>
  )
}
