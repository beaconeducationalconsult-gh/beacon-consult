/**
 * `firestore.rules`, decided by the Firestore emulator.
 *
 * `src/firestoreRules.test.js` reads the rules file and proves nobody deleted a
 * guard. It cannot prove a permission *decision* — whether an approved member
 * really can read a colleague's scheme, whether a like really cannot inflate its
 * own tally, whether an un-filtered list really is denied for an ordinary
 * member. That is what this file is for: every assertion below is a request made
 * by a real client SDK to a real rules engine, and the emulator's verdict.
 *
 * Why it lives outside `src/` and outside `make check`: the emulator is a JVM
 * program. This sandbox has no JVM and no reachable mirror for one, so the suite
 * runs in CI (`.github/workflows/ci.yml`, the `rules` job) and on any machine
 * with Java 21:
 *
 *   yarn test:rules        # starts the emulator, runs this file, shuts it down
 *
 * Running `vitest --config vitest.rules.config.js` on its own fails on purpose:
 * without the emulator there is nothing to ask.
 *
 * The cast below is the same one `docs/security.md` describes: an admin, two
 * approved members, a member with a school, a school admin, a pending member,
 * and — the case the rules comments keep pointing at — a signed-in caller with
 * no profile document at all.
 */

import { readFileSync } from 'node:fs'
import {
  initializeTestEnvironment,
  assertFails,
  assertSucceeds,
} from '@firebase/rules-unit-testing'
import {
  collection,
  deleteDoc,
  deleteField,
  doc,
  getDoc,
  getDocs,
  query,
  setDoc,
  updateDoc,
  where,
} from 'firebase/firestore'
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'

const EMULATOR = process.env.FIRESTORE_EMULATOR_HOST

if (!EMULATOR) {
  throw new Error(
    'FIRESTORE_EMULATOR_HOST is not set, so there is no emulator to ask. ' +
      'Run `yarn test:rules` — it starts the emulator and then this config.',
  )
}

const [host, port] = EMULATOR.split(':')

const RULES = readFileSync(new URL('../../firestore.rules', import.meta.url), 'utf8')

let testEnv

/** A Firestore instance acting as `uid`. */
const as = (uid) => testEnv.authenticatedContext(uid).firestore()

/** A Firestore instance with no auth token at all (the public pages). */
const anon = () => testEnv.unauthenticatedContext().firestore()

/** Write documents with the rules switched off — the "already in the database" state. */
const seed = (docs) =>
  testEnv.withSecurityRulesDisabled(async (context) => {
    const db = context.firestore()
    for (const [path, data] of Object.entries(docs)) {
      await setDoc(doc(db, path), data)
    }
  })

const CAST = {
  'users/admin': { role: 'admin', status: 'approved', displayName: 'Admin' },
  'users/alice': { role: 'member', status: 'approved', displayName: 'Alice' },
  'users/bob': { role: 'member', status: 'approved', displayName: 'Bob' },
  'users/carol': { role: 'member', status: 'approved', schoolId: 'school-1' },
  'users/head': { role: 'school_admin', status: 'approved', schoolId: 'school-1' },
  'users/pending': { role: 'member', status: 'pending' },
  'school_codes/ABC123': { schoolId: 'school-1' },
}

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: process.env.GCLOUD_PROJECT || 'demo-beacon-rules',
    firestore: { host, port: Number(port), rules: RULES },
  })
})

beforeEach(async () => {
  await testEnv.clearFirestore()
  await seed(CAST)
})

afterAll(async () => {
  await testEnv.cleanup()
})

// ── users ───────────────────────────────────────────────────────────────────

describe('users/ — the signup that cannot promote itself', () => {
  it('lets a new caller create its own profile with the two forced fields', async () => {
    await assertSucceeds(
      setDoc(doc(as('newbie'), 'users/newbie'), {
        displayName: 'Newbie',
        status: 'pending',
        role: 'member',
      }),
    )
  })

  it('refuses a signup that writes status: approved', async () => {
    await assertFails(
      setDoc(doc(as('newbie'), 'users/newbie'), {
        displayName: 'Newbie',
        status: 'approved',
        role: 'member',
      }),
    )
  })

  it('refuses a signup that writes role: admin', async () => {
    await assertFails(
      setDoc(doc(as('newbie'), 'users/newbie'), {
        displayName: 'Newbie',
        status: 'pending',
        role: 'admin',
      }),
    )
  })

  it('refuses a profile written for somebody else', async () => {
    await assertFails(
      setDoc(doc(as('newbie'), 'users/alice'), { status: 'pending', role: 'member' }),
    )
  })

  it('refuses an anonymous signup', async () => {
    await assertFails(
      setDoc(doc(anon(), 'users/newbie'), { status: 'pending', role: 'member' }),
    )
  })

  it('lets a member read a colleague profile once approved', async () => {
    await assertSucceeds(getDoc(doc(as('alice'), 'users/bob')))
  })

  it('refuses a pending member any profile but their own', async () => {
    await assertFails(getDoc(doc(as('pending'), 'users/alice')))
    await assertSucceeds(getDoc(doc(as('pending'), 'users/pending')))
  })

  it('refuses a profile read to a signed-in caller with no profile', async () => {
    // The bootstrap hole: no users/{uid} makes isApproved() error, which is a
    // denial — otherwise an unprovisioned account could read the network.
    await assertFails(getDoc(doc(as('ghost'), 'users/alice')))
  })

  it('lets a member edit their own profile', async () => {
    await assertSucceeds(
      updateDoc(doc(as('alice'), 'users/alice'), { displayName: 'Alice A.', phone: '0200' }),
    )
  })

  it('refuses a member promoting themselves to admin', async () => {
    await assertFails(updateDoc(doc(as('alice'), 'users/alice'), { role: 'admin' }))
  })

  it('refuses a member approving themselves', async () => {
    await assertFails(updateDoc(doc(as('pending'), 'users/pending'), { status: 'approved' }))
  })

  it('refuses a member moving themselves into a school', async () => {
    await assertFails(updateDoc(doc(as('alice'), 'users/alice'), { schoolId: 'school-1' }))
  })

  it('lets an admin approve and promote a member', async () => {
    await assertSucceeds(updateDoc(doc(as('admin'), 'users/pending'), { status: 'approved' }))
    await assertSucceeds(updateDoc(doc(as('admin'), 'users/bob'), { role: 'admin' }))
  })

  it('lets an admin read and delete a profile', async () => {
    await assertSucceeds(getDoc(doc(as('admin'), 'users/pending')))
    await assertSucceeds(deleteDoc(doc(as('admin'), 'users/pending')))
  })

  it('refuses a member deleting their own profile', async () => {
    await assertFails(deleteDoc(doc(as('alice'), 'users/alice')))
  })

  it('lets a school admin move a member into their own school', async () => {
    await assertSucceeds(updateDoc(doc(as('head'), 'users/alice'), { schoolId: 'school-1' }))
  })

  it('lets a school admin remove a member of their school', async () => {
    await assertSucceeds(updateDoc(doc(as('head'), 'users/carol'), { schoolId: null }))
  })

  it('refuses a school admin moving a member into another school', async () => {
    await assertFails(updateDoc(doc(as('head'), 'users/bob'), { schoolId: 'school-2' }))
  })

  it('lets a member join a school with a valid code, then drop the code', async () => {
    // The client's two-step join (Phase 2.5): write schoolId + the code, then
    // remove the code. Both steps are in the rule.
    await assertSucceeds(
      updateDoc(doc(as('alice'), 'users/alice'), { schoolId: 'school-1', joinCode: 'ABC123' }),
    )
  })

  it('refuses a join whose code belongs to a different school', async () => {
    await seed({ 'school_codes/OTHER': { schoolId: 'school-2' } })
    await assertFails(
      updateDoc(doc(as('alice'), 'users/alice'), { schoolId: 'school-1', joinCode: 'OTHER' }),
    )
  })

  it('refuses a join with a code that does not exist', async () => {
    await assertFails(
      updateDoc(doc(as('alice'), 'users/alice'), { schoolId: 'school-1', joinCode: 'NOPE' }),
    )
  })

  it('lets a member remove the join code after joining', async () => {
    await seed({ 'users/joined': { role: 'member', status: 'approved', schoolId: 'school-1', joinCode: 'ABC123' } })
    await assertSucceeds(
      updateDoc(doc(as('joined'), 'users/joined'), { joinCode: deleteField() }),
    )
  })

  it('lets an approved member provisioning a pupil login (inert Phase 3)', async () => {
    // No client writes this yet — the emulator is where a permission that only
    // exists on paper gets looked at. It is the reason an approved member may
    // create a profile for a uid that is not their own.
    await assertSucceeds(
      setDoc(doc(as('alice'), 'users/pupil1'), {
        role: 'student',
        status: 'approved',
        classroomId: 'class-1',
      }),
    )
  })

  it('refuses that provisioning when the pupil is not approved', async () => {
    await assertFails(
      setDoc(doc(as('alice'), 'users/pupil1'), {
        role: 'student',
        status: 'pending',
        classroomId: 'class-1',
      }),
    )
  })
})

// ── posts ───────────────────────────────────────────────────────────────────

describe('posts/ — approved members only, authorship pinned', () => {
  it('lets an approved member post as themselves', async () => {
    await assertSucceeds(
      setDoc(doc(as('alice'), 'posts/p1'), { authorId: 'alice', body: 'Hello' }),
    )
  })

  it('refuses a post claiming another author', async () => {
    await assertFails(
      setDoc(doc(as('alice'), 'posts/p1'), { authorId: 'bob', body: 'Hello' }),
    )
  })

  it('refuses a post from a pending member', async () => {
    await assertFails(
      setDoc(doc(as('pending'), 'posts/p1'), { authorId: 'pending', body: 'Hello' }),
    )
  })

  it('refuses the feed to anonymous and pending callers', async () => {
    await assertFails(getDoc(doc(anon(), 'posts/p1')))
    await assertFails(getDoc(doc(as('pending'), 'posts/p1')))
    await assertSucceeds(getDoc(doc(as('alice'), 'posts/p1')))
  })

  it('lets the author edit their post and nobody else', async () => {
    await seed({ 'posts/p1': { authorId: 'alice', body: 'Hello' } })
    await assertSucceeds(updateDoc(doc(as('alice'), 'posts/p1'), { body: 'Edited' }))
    await assertFails(updateDoc(doc(as('bob'), 'posts/p1'), { body: 'Hijacked' }))
  })

  it('lets another member like a post, tally and all', async () => {
    await seed({ 'posts/p1': { authorId: 'alice', body: 'Hello', likesCount: 0, likedBy: [] } })
    await assertSucceeds(
      updateDoc(doc(as('bob'), 'posts/p1'), { likesCount: 1, likedBy: ['bob'] }),
    )
  })

  it('refuses a like that inflates the tally', async () => {
    await seed({ 'posts/p1': { authorId: 'alice', body: 'Hello', likesCount: 0, likedBy: [] } })
    await assertFails(
      updateDoc(doc(as('bob'), 'posts/p1'), { likesCount: 9999, likedBy: ['bob'] }),
    )
  })

  it('refuses a like that counts somebody else', async () => {
    await seed({ 'posts/p1': { authorId: 'alice', body: 'Hello', likesCount: 0, likedBy: [] } })
    await assertFails(
      updateDoc(doc(as('bob'), 'posts/p1'), { likesCount: 1, likedBy: ['carol'] }),
    )
  })

  it('refuses a like that smuggles in another field', async () => {
    await seed({ 'posts/p1': { authorId: 'alice', body: 'Hello', likesCount: 0, likedBy: [] } })
    await assertFails(
      updateDoc(doc(as('bob'), 'posts/p1'), { likesCount: 1, likedBy: ['bob'], body: 'Hijacked' }),
    )
  })

  it('lets a member take their like back', async () => {
    await seed({ 'posts/p1': { authorId: 'alice', body: 'Hello', likesCount: 1, likedBy: ['bob'] } })
    await assertSucceeds(
      updateDoc(doc(as('bob'), 'posts/p1'), { likesCount: 0, likedBy: [] }),
    )
  })

  it('lets the author or an admin delete, and nobody else', async () => {
    await seed({
      'posts/p1': { authorId: 'alice', body: 'Hello' },
      'posts/p2': { authorId: 'alice', body: 'Hello again' },
    })
    await assertFails(deleteDoc(doc(as('bob'), 'posts/p1')))
    await assertSucceeds(deleteDoc(doc(as('alice'), 'posts/p1')))
    await assertSucceeds(deleteDoc(doc(as('admin'), 'posts/p2')))
  })
})

// ── notes ───────────────────────────────────────────────────────────────────

describe('notes/ — the visibility model', () => {
  const NOTES = {
    'notes/members': { authorId: 'bob', visibility: 'members', status: 'published', title: 'Shared' },
    'notes/private': { authorId: 'bob', visibility: 'private', status: 'draft', title: 'Draft' },
  }

  it('lets an approved member read a members note', async () => {
    await seed(NOTES)
    await assertSucceeds(getDoc(doc(as('alice'), 'notes/members')))
  })

  it('hides a private draft from everybody but its author and admins', async () => {
    await seed(NOTES)
    await assertFails(getDoc(doc(as('alice'), 'notes/private')))
    await assertSucceeds(getDoc(doc(as('bob'), 'notes/private')))
    await assertSucceeds(getDoc(doc(as('admin'), 'notes/private')))
  })

  it('keeps notes away from pending members entirely', async () => {
    await seed(NOTES)
    await assertFails(getDoc(doc(as('pending'), 'notes/members')))
  })

  it('lets a member write their own note', async () => {
    await assertSucceeds(
      setDoc(doc(as('alice'), 'notes/n1'), {
        authorId: 'alice',
        title: 'My note',
        visibility: 'members',
        status: 'published',
      }),
    )
  })

  it('refuses a note written in somebody else name', async () => {
    await assertFails(
      setDoc(doc(as('alice'), 'notes/n1'), {
        authorId: 'bob',
        title: 'Not mine',
        visibility: 'members',
        status: 'published',
      }),
    )
  })

  it('refuses a note written without the status the create rule reads', async () => {
    // `request.resource.data.status != 'school'` errors when the field is
    // absent, and an error denies. NoteForm always writes a status — this pins
    // the sharp edge so a future form cannot quietly lose the field.
    await assertFails(
      setDoc(doc(as('alice'), 'notes/n1'), { authorId: 'alice', title: 'x', visibility: 'members' }),
    )
  })

  it('scopes a school note to the author own school', async () => {
    await assertSucceeds(
      setDoc(doc(as('carol'), 'notes/school'), {
        authorId: 'carol',
        title: 'For my school',
        visibility: 'members',
        status: 'school',
        schoolId: 'school-1',
      }),
    )
    await assertFails(
      setDoc(doc(as('alice'), 'notes/school2'), {
        authorId: 'alice',
        title: 'For a school I am not in',
        visibility: 'members',
        status: 'school',
        schoolId: 'school-1',
      }),
    )
  })

  it('lets the author edit their note but never hand it over', async () => {
    await seed(NOTES)
    await assertSucceeds(updateDoc(doc(as('bob'), 'notes/members'), { title: 'Edited' }))
    await assertFails(updateDoc(doc(as('bob'), 'notes/members'), { authorId: 'alice' }))
    await assertFails(updateDoc(doc(as('alice'), 'notes/members'), { title: 'Hijacked' }))
  })

  it('lets the author delete their note and refuses everybody else', async () => {
    await seed(NOTES)
    await assertFails(deleteDoc(doc(as('alice'), 'notes/members')))
    await assertSucceeds(deleteDoc(doc(as('bob'), 'notes/members')))
  })

  it('allows the two list queries the client actually runs', async () => {
    await seed(NOTES)
    await assertSucceeds(
      getDocs(query(collection(as('alice'), 'notes'), where('authorId', '==', 'alice'))),
    )
    await assertSucceeds(
      getDocs(
        query(collection(as('alice'), 'notes'), where('visibility', 'in', ['members', 'public'])),
      ),
    )
  })

  it('denies an un-filtered list of notes to an ordinary member', async () => {
    // The bug this rule shape was rebuilt for (P2-7). If this ever passes, a
    // member can enumerate drafts the UI hides — and every scoped list in
    // src/pages/ has lost its reason to be scoped.
    await seed(NOTES)
    await assertFails(getDocs(collection(as('alice'), 'notes')))
  })

  it('still lets an admin list notes un-filtered', async () => {
    await seed(NOTES)
    await assertSucceeds(getDocs(collection(as('admin'), 'notes')))
  })
})

// ── the same visibility model on plans and forecasts ────────────────────────

for (const [collectionName, idPrefix] of [
  ['weekly_forecasts', 'schemes'],
  ['lesson_plans', 'plans'],
]) {
  describe(`${collectionName}/ — same visibility model, no like path`, () => {
    const draft = `${collectionName}/${idPrefix}-draft`
    const rows = {
      [draft]: { authorId: 'bob', visibility: 'private', title: 'Draft', week: 1 },
      [`${collectionName}/${idPrefix}-shared`]: {
        authorId: 'bob',
        visibility: 'members',
        title: 'Shared',
        week: 1,
      },
    }

    it('lets a member write their own row', async () => {
      await assertSucceeds(
        setDoc(doc(as('alice'), `${collectionName}/mine`), {
          authorId: 'alice',
          visibility: 'members',
          title: 'Mine',
          week: 1,
        }),
      )
    })

    it('refuses a row claiming another author', async () => {
      await assertFails(
        setDoc(doc(as('alice'), `${collectionName}/mine`), {
          authorId: 'bob',
          visibility: 'members',
          title: 'Mine',
          week: 1,
        }),
      )
    })

    it('hides a private draft and shares a members row', async () => {
      await seed(rows)
      await assertSucceeds(getDoc(doc(as('alice'), `${collectionName}/${idPrefix}-shared`)))
      await assertFails(getDoc(doc(as('alice'), draft)))
      await assertSucceeds(getDoc(doc(as('bob'), draft)))
    })

    it('denies an un-filtered list and allows the author-scoped one', async () => {
      await seed(rows)
      await assertFails(getDocs(collection(as('alice'), collectionName)))
      await assertSucceeds(
        getDocs(query(collection(as('alice'), collectionName), where('authorId', '==', 'alice'))),
      )
    })

    it('lets the author edit, refuses a takeover, and scopes deletes', async () => {
      await seed(rows)
      await assertSucceeds(updateDoc(doc(as('bob'), draft), { title: 'Edited' }))
      await assertFails(updateDoc(doc(as('bob'), draft), { authorId: 'alice' }))
      await assertFails(deleteDoc(doc(as('alice'), draft)))
      await assertSucceeds(deleteDoc(doc(as('bob'), draft)))
    })
  })
}

// ── the generated-document library ──────────────────────────────────────────

describe('generated_documents/ — a record may only point at your own folder', () => {
  const RECORD = {
    name: 'scheme.pdf',
    kind: 'scheme',
    bytes: 1000,
    storagePath: 'generated/alice/1700000000000-scheme.pdf',
    storageUrl: 'https://example.invalid/scheme.pdf',
    meta: {},
    authorId: 'alice',
  }

  it('lets a member record a file in their own folder', async () => {
    await assertSucceeds(setDoc(doc(as('alice'), 'generated_documents/d1'), RECORD))
  })

  it('refuses a record pointing at another member folder', async () => {
    await assertFails(
      setDoc(doc(as('alice'), 'generated_documents/d1'), {
        ...RECORD,
        storagePath: 'generated/bob/1700000000000-scheme.pdf',
      }),
    )
  })

  it('refuses a record with no storage path at all', async () => {
    const { storagePath: _omitted, ...withoutPath } = RECORD
    await assertFails(setDoc(doc(as('alice'), 'generated_documents/d1'), withoutPath))
  })

  it('shows a record to its owner and an admin, and to nobody else', async () => {
    await seed({ 'generated_documents/d1': RECORD })
    await assertSucceeds(getDoc(doc(as('alice'), 'generated_documents/d1')))
    await assertSucceeds(getDoc(doc(as('admin'), 'generated_documents/d1')))
    await assertFails(getDoc(doc(as('bob'), 'generated_documents/d1')))
  })

  it('denies an un-filtered library list and allows the owner-scoped one', async () => {
    await seed({ 'generated_documents/d1': RECORD })
    await assertFails(getDocs(collection(as('alice'), 'generated_documents')))
    const mine = await assertSucceeds(
      getDocs(
        query(collection(as('alice'), 'generated_documents'), where('authorId', '==', 'alice')),
      ),
    )
    expect(mine.size).toBe(1)
  })

  it('lets only an admin change a record, and the owner delete it', async () => {
    await seed({ 'generated_documents/d1': RECORD })
    await assertFails(updateDoc(doc(as('alice'), 'generated_documents/d1'), { name: 'x.pdf' }))
    await assertSucceeds(updateDoc(doc(as('admin'), 'generated_documents/d1'), { name: 'x.pdf' }))
    await assertFails(deleteDoc(doc(as('bob'), 'generated_documents/d1')))
    await assertSucceeds(deleteDoc(doc(as('alice'), 'generated_documents/d1')))
  })
})

// ── slide lessons and their comments ────────────────────────────────────────

describe('lesson_slides/ and its comments', () => {
  it('lets an approved member write a deck and read a colleague deck', async () => {
    await assertSucceeds(
      setDoc(doc(as('bob'), 'lesson_slides/deck1'), { authorId: 'bob', title: 'Fractions' }),
    )
    await seed({ 'lesson_slides/deck1': { authorId: 'bob', title: 'Fractions' } })
    await assertSucceeds(getDoc(doc(as('alice'), 'lesson_slides/deck1')))
  })

  it('lets the author edit a deck and refuses everybody else', async () => {
    await seed({ 'lesson_slides/deck1': { authorId: 'bob', title: 'Fractions' } })
    await assertSucceeds(updateDoc(doc(as('bob'), 'lesson_slides/deck1'), { title: 'Edited' }))
    await assertFails(updateDoc(doc(as('alice'), 'lesson_slides/deck1'), { title: 'Hijacked' }))
    await assertSucceeds(updateDoc(doc(as('admin'), 'lesson_slides/deck1'), { title: 'Moderated' }))
  })

  it('lets a member comment as themselves and edit only their own comment', async () => {
    await seed({ 'lesson_slides/deck1': { authorId: 'bob', title: 'Fractions' } })
    await assertSucceeds(
      setDoc(doc(as('alice'), 'lesson_slides/deck1/comments/c1'), {
        authorId: 'alice',
        body: 'Useful, thanks',
      }),
    )
    await seed({
      'lesson_slides/deck1/comments/c1': { authorId: 'alice', body: 'Useful, thanks' },
    })
    await assertSucceeds(
      updateDoc(doc(as('alice'), 'lesson_slides/deck1/comments/c1'), { body: 'Edited' }),
    )
    await assertFails(
      updateDoc(doc(as('bob'), 'lesson_slides/deck1/comments/c1'), { body: 'Not mine' }),
    )
  })
})

// ── quote likes ─────────────────────────────────────────────────────────────

describe('quote_likes/ — one person, one count, ±1', () => {
  it('keeps like counts away from anonymous visitors', async () => {
    await seed({ 'quote_likes/q1': { count: 1, likedBy: ['alice'] } })
    await assertFails(getDoc(doc(anon(), 'quote_likes/q1')))
    await assertSucceeds(getDoc(doc(as('alice'), 'quote_likes/q1')))
  })

  it('lets the first like create the document with a count of one', async () => {
    await assertSucceeds(setDoc(doc(as('alice'), 'quote_likes/q1'), { count: 1, likedBy: ['alice'] }))
  })

  it('refuses a document that starts with a tally of its own', async () => {
    await assertFails(setDoc(doc(as('alice'), 'quote_likes/q1'), { count: 5, likedBy: ['alice'] }))
  })

  it('refuses a first like that counts somebody else', async () => {
    await assertFails(setDoc(doc(as('alice'), 'quote_likes/q1'), { count: 1, likedBy: ['bob'] }))
  })

  it('refuses a document with fields the rule did not ask for', async () => {
    await assertFails(
      setDoc(doc(as('alice'), 'quote_likes/q1'), { count: 1, likedBy: ['alice'], extra: true }),
    )
  })

  it('lets a second member like and unlike, moving the count by one', async () => {
    await seed({ 'quote_likes/q1': { count: 1, likedBy: ['alice'] } })
    await assertSucceeds(
      updateDoc(doc(as('bob'), 'quote_likes/q1'), { count: 2, likedBy: ['alice', 'bob'] }),
    )
    await seed({ 'quote_likes/q1': { count: 2, likedBy: ['alice', 'bob'] } })
    await assertSucceeds(
      updateDoc(doc(as('bob'), 'quote_likes/q1'), { count: 1, likedBy: ['alice'] }),
    )
  })

  it('refuses a like that inflates the count', async () => {
    await seed({ 'quote_likes/q1': { count: 1, likedBy: ['alice'] } })
    await assertFails(
      updateDoc(doc(as('bob'), 'quote_likes/q1'), { count: 99, likedBy: ['alice', 'bob'] }),
    )
  })

  it('refuses a like that counts a member who did not ask for it', async () => {
    await seed({ 'quote_likes/q1': { count: 1, likedBy: ['alice'] } })
    await assertFails(
      updateDoc(doc(as('bob'), 'quote_likes/q1'), { count: 2, likedBy: ['alice', 'carol'] }),
    )
  })

  it('lets only an admin delete a like document', async () => {
    await seed({ 'quote_likes/q1': { count: 1, likedBy: ['alice'] } })
    await assertFails(deleteDoc(doc(as('alice'), 'quote_likes/q1')))
    await assertSucceeds(deleteDoc(doc(as('admin'), 'quote_likes/q1')))
  })
})

// ── progress ────────────────────────────────────────────────────────────────

describe('progress/ — the owner and their school', () => {
  it('lets a member write and read their own tracker', async () => {
    await assertSucceeds(setDoc(doc(as('alice'), 'progress/alice'), { covered: ['B1.1.1.1.1'] }))
    await assertSucceeds(getDoc(doc(as('alice'), 'progress/alice')))
  })

  it('hides a tracker from a member of no school', async () => {
    await seed({ 'progress/alice': { covered: [] } })
    await assertFails(getDoc(doc(as('bob'), 'progress/alice')))
    await assertFails(getDoc(doc(anon(), 'progress/alice')))
  })

  it('shows a tracker to a colleague in the same school', async () => {
    await seed({ 'progress/carol': { covered: [] } })
    await assertSucceeds(getDoc(doc(as('head'), 'progress/carol')))
    await assertFails(getDoc(doc(as('bob'), 'progress/carol')))
  })

  it('refuses a member writing somebody else tracker', async () => {
    await assertFails(setDoc(doc(as('bob'), 'progress/alice'), { covered: [] }))
  })
})

// ── the public pages ────────────────────────────────────────────────────────

describe('articles/ and vacancies/ — what a visitor may read', () => {
  const ARTICLES = {
    'articles/public': { authorId: 'bob', visibility: 'public', title: 'Public' },
    'articles/members': { authorId: 'bob', visibility: 'members', title: 'Members' },
    'articles/pending-draft': { authorId: 'pending', visibility: 'members', title: 'Draft' },
  }

  it('shows a public article to a visitor and hides a members article', async () => {
    await seed(ARTICLES)
    await assertSucceeds(getDoc(doc(anon(), 'articles/public')))
    await assertFails(getDoc(doc(anon(), 'articles/members')))
  })

  it('lets the anonymous public list run, because the query carries the filter', async () => {
    await seed(ARTICLES)
    await assertSucceeds(
      getDocs(query(collection(anon(), 'articles'), where('visibility', '==', 'public'))),
    )
  })

  it('lets a pending author read their own draft, and an approved member read a members article', async () => {
    await seed(ARTICLES)
    await assertSucceeds(getDoc(doc(as('pending'), 'articles/pending-draft')))
    await assertSucceeds(getDoc(doc(as('alice'), 'articles/members')))
  })

  it('refuses an anonymous write and allows an approved member', async () => {
    await assertFails(
      setDoc(doc(anon(), 'articles/a1'), { authorId: 'alice', visibility: 'public', title: 'x' }),
    )
    await assertSucceeds(
      setDoc(doc(as('alice'), 'articles/a1'), {
        authorId: 'alice',
        visibility: 'public',
        title: 'x',
      }),
    )
  })

  it('shows a published vacancy to a visitor and hides a draft', async () => {
    await seed({
      'vacancies/pub': { authorId: 'bob', status: 'published', title: 'Job' },
      'vacancies/draft': { authorId: 'bob', status: 'draft', title: 'Job' },
    })
    await assertSucceeds(getDoc(doc(anon(), 'vacancies/pub')))
    await assertFails(getDoc(doc(anon(), 'vacancies/draft')))
    await assertSucceeds(getDoc(doc(as('bob'), 'vacancies/draft')))
  })

  it('refuses an anonymous vacancy write and allows an approved member', async () => {
    await assertFails(
      setDoc(doc(anon(), 'vacancies/v1'), { authorId: 'alice', status: 'draft', title: 'x' }),
    )
    await assertSucceeds(
      setDoc(doc(as('alice'), 'vacancies/v1'), {
        authorId: 'alice',
        status: 'draft',
        title: 'x',
      }),
    )
  })
})
