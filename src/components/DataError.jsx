import EmptyState from './EmptyState'
import { dataErrorMessage } from '../lib/dataError'

/**
 * Shown when a Firestore read fails.
 *
 * Every list and detail page used to fall through to "Nothing here yet" or
 * "not found" on *any* read error, so a permission or network failure looked
 * exactly like an empty collection — the same class of bug as the empty
 * curriculum dropdowns, and the reason a fresh deployment "shows no data"
 * rather than "cannot read data".
 *
 * The copy, the two causes worth naming and the index link all live in
 * `src/lib/dataError.js`: this is the renderer, and the wording is unit-tested
 * there without Firebase.
 */
export default function DataError({ what = 'this data', error }) {
  const { code, cause, hint, link } = dataErrorMessage(error, what)

  return (
    <EmptyState
      title={`Could not load ${what}`}
      message={`${cause} (${code})`}
      action={
        <div className="flex flex-col items-center gap-3">
          {hint && <p className="max-w-md text-xs text-slate-400">{hint}</p>}
          <div className="flex flex-wrap items-center justify-center gap-2">
            {/* The console link creates the missing index; opening it in a new
                tab keeps the page (and its error) where the reader left it. */}
            {link && (
              <a className="btn-secondary text-xs" href={link.href} target="_blank" rel="noreferrer">
                {link.label}
              </a>
            )}
            <button type="button" className="btn-secondary text-xs" onClick={() => window.location.reload()}>
              Try again
            </button>
          </div>
        </div>
      }
    />
  )
}
