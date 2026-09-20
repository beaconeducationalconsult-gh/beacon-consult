import { describe, expect, it, vi, beforeEach } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import {
  isStorageMissing, probeStorage, resetStorageProbe, storageFailureMessage,
} from './generatedDocs'

/*
 * The document library's client half (P3-3).
 *
 * Two things are held here. The small one: filenames and paths — the shape the
 * rules depend on, and the names a teacher sees in their downloads folder. The
 * larger one: **every page that downloads a document offers to keep it**, which
 * is the whole point of the library and the thing that quietly rots as pages are
 * added. And the order of the write: the file is uploaded before the record is
 * created, so a failed upload cannot leave a broken entry in the library.
 */

const uploads = []
const records = []

vi.mock('../firebase', () => ({ db: { _db: true }, storage: { _storage: true } }))

vi.mock('firebase/firestore', () => ({
  addDoc: vi.fn(async (collectionRef, data) => {
    records.push({ collection: collectionRef.name, data })
    return { id: 'doc1' }
  }),
  collection: (_db, name) => ({ name }),
  deleteDoc: vi.fn(async () => {}),
  doc: (_db, name, id) => ({ name, id }),
  serverTimestamp: () => 'SERVER_TIMESTAMP',
}))

vi.mock('firebase/storage', () => ({
  ref: (_storage, path) => ({ path }),
  uploadBytesResumable: vi.fn((reference, blob) => {
    uploads.push({ path: reference.path, size: blob.size })
    const snapshot = { ref: reference, bytesTransferred: blob.size, totalBytes: blob.size }
    return {
      snapshot,
      on: (_event, progress, _error, complete) => {
        progress(snapshot)
        complete()
      },
    }
  }),
  getDownloadURL: async (reference) => `https://storage.example/${reference.path}`,
  deleteObject: vi.fn(async () => {}),
}))

const {
  MAX_UPLOAD_BYTES, checkUpload, deleteStoredDocument, documentRecord, libraryPath,
  safeFilename, saveGeneratedDocument, suggestFilename,
} = await import('./generatedDocs')

beforeEach(() => {
  uploads.length = 0
  records.length = 0
})

const blob = (size) => ({ size, type: 'application/pdf' })
const user = { uid: 'uid1', displayName: 'Mr Mensah' }

describe('filenames and paths', () => {
  it('strips what a filesystem or a URL would object to', () => {
    expect(safeFilename('Lesson_Plan/B4: "place value"?')).toBe('Lesson_PlanB4 place value')
    expect(safeFilename('   ')).toBe('document')
    expect(safeFilename(undefined)).toBe('document')
    expect(safeFilename('x'.repeat(200)).length).toBe(120)
    expect(safeFilename('tab\there')).toBe('tabhere')
  })

  it('puts every document under the member’s own folder', () => {
    const path = libraryPath('uid1', 'Lesson_Plan_B4.docx')
    expect(path.startsWith('generated/uid1/')).toBe(true)
    expect(path.endsWith('Lesson_Plan_B4.docx')).toBe(true)
    // The rules check this prefix; a path without a uid must fail loudly here
    // rather than be rejected later by Storage.
    expect(() => libraryPath('', 'x.pdf')).toThrow(/signed-in/i)
  })

  it('suggests a name a teacher will recognise', () => {
    expect(suggestFilename('question_paper', { subjectId: 'mathematics', grade: 'B4', term: 1 }, 'pdf'))
      .toBe('Exam_paper_mathematics_B4_T1.pdf')
    expect(suggestFilename('scheme', { subjectName: 'Creative Arts', grade: 'B5' }, 'docx'))
      .toBe('Scheme_of_learning_Creative_Arts_B5.docx')
  })
})

describe('what may be stored', () => {
  it('refuses an empty or oversized document before uploading anything', () => {
    expect(checkUpload(null)).toMatch(/nothing to save/i)
    expect(checkUpload(blob(MAX_UPLOAD_BYTES + 1))).toMatch(/limit is 8 MB/)
    expect(checkUpload(blob(1024))).toBe('')
  })

  it('records provenance a library can list', () => {
    const record = documentRecord({
      user, filename: 'Exam_paper.pdf', kind: 'question_paper', bytes: 2048,
      storagePath: 'generated/uid1/1-Exam_paper.pdf', meta: { grade: 'B4' },
    })
    expect(record).toMatchObject({
      kindLabel: 'Exam paper',
      bytes: 2048,
      authorId: 'uid1',
      authorName: 'Mr Mensah',
      meta: { grade: 'B4' },
    })
  })
})

describe('storing a document', () => {
  it('uploads the file before it writes the record', async () => {
    const saved = await saveGeneratedDocument({
      blob: blob(4096), filename: 'Lesson_Plan.docx', kind: 'lesson_plan',
      meta: { grade: 'B4' }, user,
    })
    expect(uploads).toHaveLength(1)
    expect(uploads[0].path.startsWith('generated/uid1/')).toBe(true)
    expect(records).toHaveLength(1)
    expect(records[0].collection).toBe('generated_documents')
    expect(records[0].data).toMatchObject({ name: 'Lesson_Plan.docx', bytes: 4096, authorId: 'uid1' })
    expect(records[0].data.storageUrl).toContain('https://storage.example/')
    expect(records[0].data.createdAt).toBe('SERVER_TIMESTAMP')
    expect(saved.id).toBe('doc1')
  })

  it('writes no record when the upload fails', async () => {
    // The order is the guarantee: upload first, record second. A record created
    // first would sit in the library pointing at a file that never arrived.
    const { uploadBytesResumable } = await import('firebase/storage')
    uploadBytesResumable.mockImplementationOnce(() => ({
      snapshot: { ref: { path: 'generated/uid1/x.pdf' } },
      on: (_event, _progress, error) => error(new Error('network gone')),
    }))

    await expect(saveGeneratedDocument({
      blob: blob(1024), filename: 'x.pdf', kind: 'note', user,
    })).rejects.toThrow('network gone')
    expect(records).toHaveLength(0)
  })

  it('refuses to store anything for a signed-out visitor', async () => {
    await expect(saveGeneratedDocument({ blob: blob(10), filename: 'x.pdf', kind: 'note', user: null }))
      .rejects.toThrow(/sign in/i)
  })

  it('deletes the record even when the file is already gone', async () => {
    const { deleteObject } = await import('firebase/storage')
    deleteObject.mockRejectedValueOnce({ code: 'storage/object-not-found' })
    await expect(deleteStoredDocument({ id: 'doc1', storagePath: 'generated/uid1/x.pdf' })).resolves.toBeUndefined()
  })
})

describe('every page that downloads a document can also keep it', () => {
  const pagesDir = new URL('../pages/', import.meta.url)
  const pages = readdirSync(pagesDir).filter((name) => name.endsWith('.jsx'))

  it('scans the pages', () => {
    expect(pages.length).toBeGreaterThan(20)
  })

  it.each(pages.filter((name) => {
    const text = readFileSync(new URL(name, pagesDir), 'utf8')
    return /download[A-Z]\w*\(/.test(text)
  }))('%s offers SaveToLibrary', (name) => {
    const text = readFileSync(new URL(name, pagesDir), 'utf8')
    expect(text, `${name} downloads a document but never offers to keep it`).toContain('SaveToLibrary')
  })
})


/*
 * Storage is optional, and the app has to tell the difference between "you have
 * saved nothing yet" and "this project has no bucket at all".
 *
 * Cloud Storage for Firebase has required the pay-as-you-go (Blaze) plan since
 * October 2024, so a school can run the entire portal — curriculum, planners,
 * exam papers, exports — with no library. Before this, pressing "Save to
 * library" on such a project produced a toast reading `storage/unknown`, which
 * names neither the cause nor the fact that the download still worked.
 */
describe('a project with no Storage bucket is not an error state', () => {
  it('recognises the 404 the SDK reports for a missing bucket', () => {
    expect(isStorageMissing({
      code: 'storage/unknown',
      message: 'Firebase Storage: An unknown error occurred, please check the error payload for server response.',
      serverResponse: '{"error":{"code":404,"message":"Not Found."}}',
    })).toBe(true)
    expect(isStorageMissing({ code: 'storage/bucket-not-found' })).toBe(true)
    expect(isStorageMissing({ message: 'bucket does not exist' })).toBe(true)
  })

  it('does not mistake other failures for a missing bucket', () => {
    // The one that matters: an enabled bucket answers a read for a path that
    // does not exist with object-not-found, and treating that as "no Storage"
    // would hide the library on every working project.
    expect(isStorageMissing({ code: 'storage/object-not-found' })).toBe(false)
    expect(isStorageMissing({ code: 'storage/unauthorized' })).toBe(false)
    expect(isStorageMissing({ code: 'storage/retry-limit-exceeded' })).toBe(false)
    expect(isStorageMissing(new Error('network down'))).toBe(false)
  })

  it('says what happened and what still works', () => {
    const message = storageFailureMessage({ code: 'storage/unknown', serverResponse: '{"error":{"code":404}}' })
    expect(message).toContain('no Firebase Storage bucket')
    expect(message).toContain('still downloads')
    expect(message).not.toContain('storage/unknown')
  })

  it('keeps the raw code for the failures a developer has to chase', () => {
    expect(storageFailureMessage({ code: 'storage/unauthorized' })).toContain('storage.rules')
    expect(storageFailureMessage({ code: 'storage/retry-limit-exceeded' })).toContain('connection')
    expect(storageFailureMessage({ code: 'storage/quota-exceeded' })).toContain('quota')
    expect(storageFailureMessage({ code: 'storage/weird' })).toContain('storage/weird')
  })

  it('probes once, and reads the answer the way a real bucket answers', async () => {
    resetStorageProbe()
    const objectNotFound = vi.fn(async () => { throw { code: 'storage/object-not-found' } })
    expect(await probeStorage(objectNotFound)).toBe('enabled')
    // Cached: the answer cannot change while the page is open.
    expect(await probeStorage(vi.fn(async () => { throw { code: 'storage/unknown' } }))).toBe('enabled')
    expect(objectNotFound).toHaveBeenCalledTimes(1)

    resetStorageProbe()
    const noBucket = vi.fn(async () => {
      throw { code: 'storage/unknown', serverResponse: '{"error":{"code":404,"message":"Not Found."}}' }
    })
    expect(await probeStorage(noBucket)).toBe('missing')
  })
})
