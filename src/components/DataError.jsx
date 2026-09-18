import EmptyState from './EmptyState'

/**
 * Shown when a Firestore read fails.
 *
 * Every list and detail page used to fall through to "Nothing here yet" or
 * "not found" on *any* read error, so a permission or network failure looked
 * exactly like an empty collection — the same class of bug as the empty
 * curriculum dropdowns, and the reason a fresh deployment "shows no data"
 * rather than "cannot read data".
 *
 * The likely causes, in order:
 *
 *   permission-denied  the account is still `status: 'pending'`, or
 *                      `firestore.rules` has not been deployed yet
 *                      (`firebase deploy --only firestore:rules`).
 *   unavailable        offline, or the project id is wrong.
 *   failed-precondition  a composite index is missing — the console error
 *                      carries a link that creates it.
 */
export default function DataError({ what = 'this data', error }) {
  const code = error?.code || 'unknown'

  const cause =
    code === 'permission-denied'
      ? `Your account does not have access to ${what}. A newly created account stays pending until an administrator approves it.`
      : code === 'unavailable'
        ? `The server could not be reached to load ${what}. Check your connection, then try again.`
        : code === 'failed-precondition'
          ? `This query needs a database index that has not been created yet.`
          : `Something went wrong while loading ${what}.`

  return (
    <EmptyState
      title={`Could not load ${what}`}
      message={`${cause} (${code})`}
      action={
        <button type="button" className="btn-secondary mt-2" onClick={() => window.location.reload()}>
          Try again
        </button>
      }
    />
  )
}
