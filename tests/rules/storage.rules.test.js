/**
 * `storage.rules`, decided by the Storage emulator.
 *
 * The sibling of firestore.rules.test.js, and the only test of this file that
 * a *decision* rather than the presence of a guard: the library's files live in
 * Cloud Storage under `generated/{uid}/…`, the uid in the path is the whole
 * permission, and the Storage emulator is the one place that can be checked
 * before the rules are published (they have never been deployed).
 *
 * Note the cross-service part: every rule here reads `users/{uid}` through
 * `firestore.get()` to decide approved/admin, exactly as production does — the
 * emulator suite wires the two emulators together for this, which is why the
 * script starts both (`--only firestore,storage`).
 */

import { readFileSync } from 'node:fs'
import {
  initializeTestEnvironment,
  assertFails,
  assertSucceeds,
} from '@firebase/rules-unit-testing'
import { doc, setDoc } from 'firebase/firestore'
import { deleteObject, getBytes, listAll, ref, uploadBytes } from 'firebase/storage'
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'

const [FIRESTORE_HOST, STORAGE_HOST] = [
  process.env.FIRESTORE_EMULATOR_HOST,
  process.env.FIREBASE_STORAGE_EMULATOR_HOST,
]

if (!FIRESTORE_HOST || !STORAGE_HOST) {
  throw new Error(
    'The emulators are not running (FIRESTORE_EMULATOR_HOST / ' +
      'FIREBASE_STORAGE_EMULATOR_HOST are unset). Run `yarn test:rules`.',
  )
}

const [fsHost, fsPort] = FIRESTORE_HOST.split(':')
const [gsHost, gsPort] = STORAGE_HOST.split(':')

const FIRESTORE_RULES = readFileSync(new URL('../../firestore.rules', import.meta.url), 'utf8')
const STORAGE_RULES = readFileSync(new URL('../../storage.rules', import.meta.url), 'utf8')

const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

let testEnv

const storageAs = (uid) => testEnv.authenticatedContext(uid).storage()
const storageAnon = () => testEnv.unauthenticatedContext().storage()

const seed = (docs) =>
  testEnv.withSecurityRulesDisabled(async (context) => {
    const db = context.firestore()
    for (const [path, data] of Object.entries(docs)) {
      await setDoc(doc(db, path), data)
    }
  })

const CAST = {
  'users/admin': { role: 'admin', status: 'approved' },
  'users/alice': { role: 'member', status: 'approved' },
  'users/bob': { role: 'member', status: 'approved' },
  'users/pending': { role: 'member', status: 'pending' },
}

/** One byte is enough; the rules never look inside the file. */
const bytes = (size = 8) => new Uint8Array(size)

const upload = (storage, path, blob = bytes()) => uploadBytes(ref(storage, path), blob)

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: process.env.GCLOUD_PROJECT || 'demo-beacon-rules',
    firestore: { host: fsHost, port: Number(fsPort), rules: FIRESTORE_RULES },
    storage: { host: gsHost, port: Number(gsPort), rules: STORAGE_RULES },
  })
})

beforeEach(async () => {
  await testEnv.clearFirestore()
  await testEnv.clearStorage()
  await seed(CAST)
})

afterAll(async () => {
  await testEnv.cleanup()
})

describe('generated/ — the uid in the path is the permission', () => {
  it('lets an approved member store a file in their own folder', async () => {
    await assertSucceeds(upload(storageAs('alice'), 'generated/alice/1-scheme.pdf'))
  })

  it('refuses a file written into another member folder', async () => {
    await assertFails(upload(storageAs('alice'), 'generated/bob/1-scheme.pdf'))
  })

  it('refuses a pending member, and an anonymous caller, outright', async () => {
    await assertFails(upload(storageAs('pending'), 'generated/pending/1-scheme.pdf'))
    await assertFails(upload(storageAnon(), 'generated/anon/1-scheme.pdf'))
  })

  it('lets an admin store under their own uid like anybody else', async () => {
    await assertSucceeds(upload(storageAs('admin'), 'generated/admin/1-scheme.pdf'))
  })

  it('caps an upload at 8 MiB, in the rule and not only in the client', async () => {
    await assertSucceeds(upload(storageAs('alice'), 'generated/alice/small.pdf', bytes(1024)))
    await assertFails(
      upload(storageAs('alice'), 'generated/alice/big.pdf', bytes(MAX_UPLOAD_BYTES + 1)),
    )
  })

  it('lets the owner read their file back, and an admin, but not a colleague', async () => {
    await assertSucceeds(upload(storageAs('alice'), 'generated/alice/1-scheme.pdf'))
    await assertSucceeds(getBytes(ref(storageAs('alice'), 'generated/alice/1-scheme.pdf')))
    await assertSucceeds(getBytes(ref(storageAs('admin'), 'generated/alice/1-scheme.pdf')))
    await assertFails(getBytes(ref(storageAs('bob'), 'generated/alice/1-scheme.pdf')))
    await assertFails(getBytes(ref(storageAnon(), 'generated/alice/1-scheme.pdf')))
  })

  it('lets the owner enumerate their own folder and nobody else folder', async () => {
    await assertSucceeds(upload(storageAs('alice'), 'generated/alice/1-scheme.pdf'))
    const mine = await assertSucceeds(listAll(ref(storageAs('alice'), 'generated/alice')))
    expect(mine.items.map((item) => item.name)).toEqual(['1-scheme.pdf'])
    await assertFails(listAll(ref(storageAs('bob'), 'generated/alice')))
    await assertFails(listAll(ref(storageAnon(), 'generated/alice')))
  })

  it('lets the owner delete their file and refuses a colleague', async () => {
    await assertSucceeds(upload(storageAs('alice'), 'generated/alice/1-scheme.pdf'))
    await assertFails(deleteObject(ref(storageAs('bob'), 'generated/alice/1-scheme.pdf')))
    await assertSucceeds(deleteObject(ref(storageAs('alice'), 'generated/alice/1-scheme.pdf')))
  })
})

describe('everything outside generated/ is denied', () => {
  it('refuses a member writing outside generated/', async () => {
    await assertFails(upload(storageAs('alice'), 'avatars/alice.png'))
  })

  it('refuses a member writing in generated/ without a uid of their own', async () => {
    await assertFails(upload(storageAs('alice'), 'generated/1-scheme.pdf'))
  })

  it('refuses an admin writing outside generated/ too', async () => {
    // The rule is path-shaped, not role-shaped: admins read any folder, but
    // they do not get a second write path.
    await assertFails(upload(storageAs('admin'), 'avatars/admin.png'))
  })

  it('refuses reads outside generated/, for members, admins and visitors', async () => {
    await assertFails(getBytes(ref(storageAs('alice'), 'avatars/alice.png')))
    await assertFails(getBytes(ref(storageAs('admin'), 'avatars/alice.png')))
    await assertFails(getBytes(ref(storageAnon(), 'avatars/alice.png')))
  })
})
