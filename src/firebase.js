import { initializeApp } from 'firebase/app'
import {
  initializeFirestore,
  persistentLocalCache,
  persistentMultipleTabManager,
} from 'firebase/firestore'
import { getAuth } from 'firebase/auth'

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

if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
  // Loud in the console, because the alternative is an opaque
  // "auth/invalid-api-key" much later. See docs/gotchas.md.
  console.error(
    '[beacon] Firebase config is missing. Copy .env.example to .env.local and fill in ' +
      'the VITE_FIREBASE_* values from the Firebase console, then restart the dev server.'
  )
}

export const app = initializeApp(firebaseConfig)

// Offline-first: reads come from IndexedDB, writes queue when offline and sync
// on reconnect. Pages need no changes — see docs/pwa-offline.md.
export const db = initializeFirestore(app, {
  localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
})

export const auth = getAuth(app)
