import { initializeApp } from 'firebase/app'
import {
  initializeFirestore,
  persistentLocalCache,
  persistentMultipleTabManager,
} from 'firebase/firestore'
import { getAuth } from 'firebase/auth'
import { getStorage } from 'firebase/storage'

// Firebase web config. These are public identifiers, not secrets — but the app
// cannot reach Firebase without them, and Vite embeds them at BUILD time, so a
// build with empty values fails at runtime, not at build time. See .env.example.
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

/**
 * Whether the six VITE_FIREBASE_* values were supplied at build time.
 *
 * When they are not, the app must not call getAuth(): the SDK throws
 * `auth/invalid-api-key` during module evaluation, which aborts the entry
 * module and leaves a blank page with nothing to act on. main.jsx checks this
 * flag and renders SetupNotice instead, so a missing config explains itself.
 */
export const firebaseConfigured = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId)

if (!firebaseConfigured) {
  console.error(
    '[beacon] Firebase config is missing. Copy .env.example to .env.local and fill in ' +
      'the VITE_FIREBASE_* values from the Firebase console, then restart the dev server.'
  )
}

export const app = firebaseConfigured ? initializeApp(firebaseConfig) : null

// Offline-first: reads come from IndexedDB, writes queue when offline and sync
// on reconnect. Pages need no changes — see docs/pwa-offline.md.
export const db = app
  ? initializeFirestore(app, {
      localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
    })
  : null

export const auth = app ? getAuth(app) : null

// The document library (P3-3) keeps generated files here. Null in a build with
// no config, exactly like db and auth, so the library degrades to a message
// instead of throwing on import. See src/lib/generatedDocs.js and storage.rules.
export const storage = app ? getStorage(app) : null
