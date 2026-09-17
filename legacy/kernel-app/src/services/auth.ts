import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  type User,
} from 'firebase/auth'
import { auth } from './firebase'

const provider = new GoogleAuthProvider()

export const signInWithGoogle = () => signInWithPopup(auth, provider)
export const signOutUser = () => signOut(auth)
export const onAuthChanged = (cb: (user: User | null) => void) =>
  onAuthStateChanged(auth, cb)
