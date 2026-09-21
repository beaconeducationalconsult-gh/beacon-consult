import Button from '../ui/Button'

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
      <p className="mt-6 text-center text-xs text-subtle">
        {loaded} shown — that is everything.
      </p>
    ) : null
  }

  return (
    <div className="mt-6 flex flex-col items-center gap-2">
      <Button variant="secondary" onClick={onLoad} loading={loading}>
        {loading ? 'Loading…' : 'Load more'}
      </Button>
      <p className="text-xs text-subtle">{loaded} shown</p>
      {error && (
        <p className="text-xs text-danger-600 dark:text-danger-500">
          More could not be loaded ({error.code || error.message || 'error'}). Refresh to try again.
        </p>
      )}
    </div>
  )
}
