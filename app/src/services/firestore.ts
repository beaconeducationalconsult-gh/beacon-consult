import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where,
  addDoc,
  serverTimestamp,
} from 'firebase/firestore'
import { db } from './firebase'
import type { Indicator } from '../kernel/types'

// ── School ───────────────────────────────────────────────────
export async function getSchool(schoolId: string) {
  const snap = await getDoc(doc(db, 'schools', schoolId))
  return snap.exists() ? snap.data() : null
}

export async function getUser(uid: string) {
  const snap = await getDoc(doc(db, 'users', uid))
  return snap.exists() ? snap.data() : null
}

// ── Generation history ───────────────────────────────────────
export async function recordGeneration(payload: {
  schoolId: string
  userId: string
  subject: string
  grade: string
  indicatorCode: string
  documentType: 'lesson_plan' | 'scheme_of_work' | 'record_of_work'
  filename: string
}) {
  return addDoc(collection(db, 'generated_materials'), {
    ...payload,
    generatedAt: serverTimestamp(),
  })
}

export async function getGenerationHistory(schoolId: string) {
  const q = query(
    collection(db, 'generated_materials'),
    where('schoolId', '==', schoolId)
  )
  const snap = await getDocs(q)
  return snap.docs.map((d) => ({ id: d.id, ...d.data() }))
}
