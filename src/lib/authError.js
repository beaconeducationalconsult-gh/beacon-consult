/*
 * What to say when sign-in fails — kept pure so it is testable.
 *
 * Both auth screens used to fall through to `err.message`, which is Firebase's
 * own text. For the two failures a **new project** produces, that text is
 * actively unhelpful:
 *
 *   auth/operation-not-allowed  "Firebase: Error (auth/operation-not-allowed)."
 *   auth/unauthorized-domain    "Firebase: Error (auth/unauthorized-domain)."
 *
 * Both mean "a console step has not been done yet", both are fixed in seconds
 * once you know which step, and neither is guessable from the code. The people
 * who meet them are also the people running the deploy, so the message names
 * the console path. See docs/build-deploy.md (Setting up a new Firebase project).
 */

const MESSAGES = {
  // ── The project is not set up yet ────────────────────────────────────────
  'auth/operation-not-allowed':
    'This project has not enabled email and password sign-in yet. Firebase console → '
    + 'Authentication → Sign-in method → Email/Password → Enable.',
  'auth/configuration-not-found':
    'This project has no Authentication set up yet. Firebase console → Authentication → '
    + 'Get started, then enable the Email/Password provider.',
  'auth/unauthorized-domain':
    'This web address is not authorized for sign-in. Firebase console → Authentication → '
    + 'Settings → Authorized domains → add it.',
  'auth/invalid-api-key':
    'The Firebase configuration in this build is not valid. Check the six VITE_FIREBASE_* '
    + 'values (Vercel → Settings → Environment Variables, and .env.local locally).',
  'auth/api-key-not-valid.-please-pass-a-valid-api-key.':
    'The Firebase configuration in this build is not valid. Check the six VITE_FIREBASE_* '
    + 'values (Vercel → Settings → Environment Variables, and .env.local locally).',

  // ── The credentials are wrong ────────────────────────────────────────────
  'auth/invalid-credential': 'That email and password do not match.',
  'auth/invalid-login-credentials': 'That email and password do not match.',
  'auth/wrong-password': 'That email and password do not match.',
  'auth/user-not-found': 'No account found for that email. Request access first.',
  'auth/invalid-email': 'That does not look like an email address.',
  'auth/email-already-in-use': 'That email is already registered. Try signing in instead.',
  'auth/weak-password': 'Choose a password with at least 8 characters.',

  // ── The account itself ───────────────────────────────────────────────────
  'auth/user-disabled': 'This account has been disabled. Contact a Beacon administrator.',
  'auth/requires-recent-login': 'Please sign in again to make that change.',

  // ── The network ──────────────────────────────────────────────────────────
  'auth/network-request-failed':
    'Firebase could not be reached. Check your connection and try again.',
  'auth/too-many-requests': 'Too many attempts. Wait a minute, then try again.',

  // ── Firestore, on the path after a successful sign-up ────────────────────
  'permission-denied':
    'Your account was created, but saving your membership was refused. The project\'s '
    + 'firestore.rules have not been published yet (or your account is suspended) — see '
    + 'docs/build-deploy.md step 6.',
  'unavailable': 'Firebase could not be reached. Check your connection and try again.',
}

/** The sentence to show for any auth (or sign-up-time Firestore) failure. */
export function authMessage(error) {
  const code = error?.code || ''
  if (MESSAGES[code]) return MESSAGES[code]
  // Never swallow information: an unrecognised code keeps Firebase's own text,
  // which is at least searchable, rather than a generic "something went wrong".
  return error?.message || 'Something went wrong. Try again.'
}

/** True when the failure means "the project is not configured yet", not "bad password". */
export function isSetupError(error) {
  return [
    'auth/operation-not-allowed', 'auth/configuration-not-found',
    'auth/unauthorized-domain', 'auth/invalid-api-key', 'permission-denied',
  ].includes(error?.code || '')
}
