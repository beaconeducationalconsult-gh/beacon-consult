/*
 * What to say when a Firestore read fails — kept pure so it is testable.
 *
 * `DataError.jsx` used to carry this copy inline, and two of the four cases
 * were dead ends for whoever hit them:
 *
 *   failed-precondition  Firestore's own message contains the console link that
 *                        creates the missing composite index. The page said
 *                        "a database index that has not been created yet" and
 *                        sent the reader hunting through the console by hand —
 *                        the index is one click away, in the error they were
 *                        already looking at.
 *   permission-denied    The most common cause on a fresh deploy is not the
 *                        account at all: it is `firestore.rules` published
 *                        before the build that queries it. Saying "you are
 *                        pending" to an approved member sends them to the wrong
 *                        place, so the message now names both causes.
 *
 * Nothing here imports Firebase, so `src/lib/dataError.test.js` runs in the
 * plain suite (`yarn test`) rather than needing the emulator.
 */

/** The index-creation link Firestore puts in a `failed-precondition` message. */
const INDEX_LINK = /https:\/\/console\.firebase\.google\.com\/\S+/

/**
 * The console URL that creates the index this query needs, or null.
 *
 * Trailing punctuation is stripped: the SDK ends the sentence with the URL, and
 * some versions punctuate after it — a link that swallows a full stop 404s.
 */
export function indexUrlFrom(error) {
  const match = INDEX_LINK.exec(String(error?.message || ''))
  return match ? match[0].replace(/[.,;)\]]+$/, '') : null
}

/**
 * `{ code, cause, hint, link }` for an error from any of the list/detail hooks.
 *
 * `cause` is one sentence; `hint` is the "so what do I do" line and may name a
 * repo file or a deploy step, because the people who read this most often are
 * running the deploy. `link` is `{ href, label }` or null.
 */
export function dataErrorMessage(error, what = 'this data') {
  const code = error?.code || 'unknown'

  if (code === 'permission-denied') {
    return {
      code,
      cause: `Your account does not have access to ${what}. A newly created account stays pending until an administrator approves it.`,
      hint: 'Already an approved member, and this worked before? Then the published rules are older than this build — re-publish firestore.rules. An old client also gets this once the new rules are live, which is why the rules go out after the build (docs/verification.md).',
      link: null,
    }
  }

  if (code === 'unavailable') {
    return {
      code,
      cause: `The server could not be reached to load ${what}.`,
      hint: 'Check the connection and try again. The curriculum you have already opened still works offline; a list you have never opened needs the server once.',
      link: null,
    }
  }

  if (code === 'failed-precondition') {
    const href = indexUrlFrom(error)
    return {
      code,
      cause: `This query needs a database index that this project does not have yet, so ${what} cannot be listed.`,
      hint: href
        ? 'The link below opens Firebase with the index already filled in — click Create index, wait a minute for it to build, then reload this page.'
        : 'Add the matching entry to firestore.indexes.json and run `firebase deploy --only firestore:indexes` (or create it from the Firebase console, Firestore → Indexes).',
      link: href ? { href, label: 'Create the missing index' } : null,
    }
  }

  if (code === 'unauthenticated') {
    return {
      code,
      cause: `You are not signed in any more, so ${what} could not be loaded.`,
      hint: 'Sign in again — the session expired.',
      link: null,
    }
  }

  return {
    code,
    cause: `Something went wrong while loading ${what}.`,
    hint: 'Try again. If it keeps happening, note this code and the page you were on (docs/verification.md, "Record what you saw").',
    link: null,
  }
}
