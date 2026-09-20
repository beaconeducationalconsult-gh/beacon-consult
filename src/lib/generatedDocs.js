/*
 * The document library (P3-3).
 *
 * Every document the portal produces — a lesson plan, a scheme, an exam paper, a
 * quiz deck, a study note — was generated in the browser and downloaded once. If
 * the teacher lost the file, the only way back was to rebuild it, because only
 * Firestore metadata was ever kept.
 *
 * This module stores the file itself in Firebase Storage and a small record in
 * Firestore, so the library can hand it back later:
 *
 *   Storage   generated/{uid}/{timestamp}-{filename}
 *   Firestore generated_documents/{id}   name, kind, bytes, storagePath, meta
 *
 * Access is enforced by `storage.rules`, not by this file: a member may only
 * write under their own uid, may only read back their own documents (admins may
 * read all), and anything outside `generated/` is denied. The path is built here
 * so the client and the rules agree on its shape — and the collection name is a
 * literal everywhere on purpose, because `src/firestoreRules.test.js` scans the
 * client source for `collection(db, '…')` and fails when one has no rule.
 */

import { addDoc, collection, deleteDoc, doc, serverTimestamp } from 'firebase/firestore'
import { deleteObject, getDownloadURL, getMetadata, ref, uploadBytesResumable } from 'firebase/storage'
import { db, storage } from '../firebase'

/** Keep in step with the size limit in storage.rules. */
export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

/** What the library calls each kind of document. */
export const DOC_KINDS = {
  lesson_plan: 'Lesson plan',
  scheme: 'Scheme of learning',
  question_paper: 'Exam paper',
  quiz_deck: 'Quiz slideshow',
  slide_deck: 'Lesson slides',
  note: 'Study note',
}

/** A filename safe for Storage and for the teacher's downloads folder. */
export function safeFilename(name) {
  // Control characters are stripped by code point rather than with a character
  // range in a regex, because ESLint (rightly) flags \x00-\x1f there.
  const cleaned = [...String(name || 'document')]
    .filter((character) => character.codePointAt(0) > 31)
    .join('')
    .replace(/[<>:"/\\|?*]/g, '')
    .trim()
  return cleaned.slice(0, 120) || 'document'
}

/**
 * Where a document lives in Storage: one folder per member.
 *
 * The uid in the path is what `storage.rules` checks, so it is not decoration —
 * a path built any other way would be rejected, which is the point.
 */
export function libraryPath(uid, filename) {
  if (!uid) throw new Error('A signed-in member is needed to store a document.')
  return `generated/${uid}/${Date.now()}-${safeFilename(filename)}`
}

/** The Firestore record for a stored document. */
export function documentRecord({ user, filename, kind, bytes, storagePath, storageUrl, meta }) {
  return {
    name: safeFilename(filename),
    kind,
    kindLabel: DOC_KINDS[kind] || kind,
    bytes: Number(bytes) || 0,
    storagePath,
    storageUrl: storageUrl || '',
    meta: meta || {},
    authorId: user.uid,
    authorName: user.displayName || user.email || 'Member',
  }
}

/*
 * Storage is **optional**, and the app has to say so in words a teacher can act on.
 *
 * Cloud Storage for Firebase has required the pay-as-you-go (Blaze) plan since
 * October 2024 — a project on the free Spark plan cannot have a bucket at all,
 * which is why a school can be running the whole portal with no library. When
 * that is the case, a save is not a bug and must not read like one: the old
 * failure was a toast saying `Could not save to your library: storage/unknown`,
 * which names neither the cause nor the (non-)consequence — the file the teacher
 * just downloaded is unaffected either way.
 */

/**
 * Storage failures that prove the bucket answered us.
 *
 * These are the difference between "the library is off" and "something went
 * wrong in a working library", and getting it backwards would hide the button on
 * every healthy project: a provisioned bucket replies to a read of a path that
 * does not exist with `object-not-found`, which is not the same thing at all.
 */
const BUCKET_ANSWERED = new Set([
  'storage/object-not-found', 'storage/unauthorized', 'storage/unauthenticated',
  'storage/canceled', 'storage/retry-limit-exceeded', 'storage/quota-exceeded',
  'storage/invalid-argument', 'storage/invalid-format', 'storage/invalid-checksum',
  'storage/invalid-url', 'storage/invalid-event-name', 'storage/invalid-root-operation',
  'storage/app-deleted',
])

/** Does this error mean "this project has no Storage bucket"? */
export function isStorageMissing(error) {
  if (!storage) return true
  const code = error?.code || ''
  if (code === 'storage/bucket-not-found') return true
  if (BUCKET_ANSWERED.has(code)) return false
  // `storage/unknown` (or no code at all) with a 404 is what a project without a
  // bucket answers to everything. The message fallback covers SDKs that phrase
  // it differently; it insists on the word "bucket" so that "Object '…' does not
  // exist" can never be read as "this project has no Storage".
  const payload = `${error?.serverResponse || ''} ${error?.message || ''}`
  return /\b404\b|not found|bucket.*(not exist|missing)/i.test(payload)
}

/** The sentence to show for any Storage failure. */
export function storageFailureMessage(error) {
  if (isStorageMissing(error)) {
    return 'This project has no Firebase Storage bucket, so the library is off. ' +
      'Everything you export still downloads to your computer — see docs/build-deploy.md.'
  }
  const code = error?.code || ''
  if (code === 'storage/unauthorized' || code === 'storage/unauthenticated') {
    return 'You are not allowed to store documents here. Sign in again, or ask an administrator ' +
      'to publish storage.rules.'
  }
  if (code === 'storage/canceled') return 'The save was cancelled.'
  if (code === 'storage/retry-limit-exceeded') return 'The connection dropped during the save. Try again.'
  if (code === 'storage/quota-exceeded') return 'The project has run out of Storage quota.'
  return `Could not save to your library: ${code || error?.message || 'unknown error'}`
}

/**
 * Ask the bucket whether it exists, once per session.
 *
 * `getMetadata` on a path that certainly does not exist is the cheapest honest
 * probe there is: an enabled bucket answers `storage/object-not-found`, a project
 * without one answers the 404 that `isStorageMissing` recognises, and the caller
 * can then hide the button or explain the page instead of offering work that
 * cannot succeed. Cached per module (per page load): the answer cannot change
 * while the page is open.
 *
 * The read function is injectable so this can be tested without Firebase.
 */
let storageProbe = null
export function probeStorage(readMetadata = getMetadata) {
  if (!storage) return Promise.resolve('missing')
  if (storageProbe) return storageProbe
  storageProbe = readMetadata(ref(storage, 'generated/__probe__/__none__'))
    .then(() => 'enabled')
    .catch((error) => (isStorageMissing(error) ? 'missing' : 'enabled'))
  return storageProbe
}

/** Forget the cached probe — for tests, and for a retry after enabling Storage. */
export function resetStorageProbe() {
  storageProbe = null
}

/** Check before a byte leaves the browser — the rules check again, server-side. */
export function checkUpload(blob) {
  if (!storage) return 'Storage is not configured in this build.'
  if (!blob || !blob.size) return 'There is nothing to save.'
  if (blob.size > MAX_UPLOAD_BYTES) {
    return `The document is ${(blob.size / 1024 / 1024).toFixed(1)} MB — the limit is ` +
      `${MAX_UPLOAD_BYTES / 1024 / 1024} MB.`
  }
  return ''
}

/**
 * Store a generated document, and record it.
 *
 * Deliberately upload-first: a Firestore record pointing at a file that never
 * arrived would show up in the library as a broken entry. If the upload fails,
 * nothing is written — the caller shows the error and the teacher still has the
 * file they just downloaded.
 */
export async function saveGeneratedDocument({ blob, filename, kind, meta, user, onProgress }) {
  const problem = checkUpload(blob)
  if (problem) throw new Error(problem)
  if (!user?.uid) throw new Error('Sign in to keep documents in your library.')

  const storagePath = libraryPath(user.uid, filename)
  const task = uploadBytesResumable(ref(storage, storagePath), blob, {
    contentType: blob.type || 'application/octet-stream',
  })

  await new Promise((resolve, reject) => {
    task.on('state_changed', (snapshot) => {
      onProgress?.(snapshot.bytesTransferred / Math.max(1, snapshot.totalBytes))
    }, reject, resolve)
  })

  const storageUrl = await getDownloadURL(task.snapshot.ref)
  const record = documentRecord({
    user, filename, kind, bytes: blob.size, storagePath, storageUrl, meta,
  })
  const saved = await addDoc(collection(db, 'generated_documents'), {
    ...record,
    createdAt: serverTimestamp(),
  })
  return { id: saved.id, ...record }
}

/** Put a stored document back in the teacher's downloads folder. */
export async function openStoredDocument(record) {
  const url = record.storageUrl || await getDownloadURL(ref(storage, record.storagePath))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = record.name
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

/** Remove both halves: the file, then the record. */
export async function deleteStoredDocument(record) {
  try {
    await deleteObject(ref(storage, record.storagePath))
  } catch (error) {
    // A missing file must not strand the record: the library's job is to hold
    // what exists, so carry on and delete the entry.
    if (error?.code !== 'storage/object-not-found') throw error
  }
  await deleteDoc(doc(db, 'generated_documents', record.id))
}

/** A filename a teacher will recognise, e.g. `Exam_paper_mathematics_B4_T1.pdf`. */
export function suggestFilename(kind, meta = {}, extension) {
  const parts = [
    DOC_KINDS[kind] || kind,
    meta.subjectId || meta.subjectName,
    meta.grade,
    meta.term ? `T${meta.term}` : null,
  ].filter(Boolean)
  // A single separator: subject names arrive with spaces ("Creative Arts"), and
  // mixing them with underscores reads like a typo in a downloads folder.
  const base = safeFilename(parts.join('_').replace(/\s+/g, '_'))
  return `${base}.${extension || 'pdf'}`
}
