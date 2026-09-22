import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { usePagedCollection } from '../hooks/useCollection'
import LoadMore from '../components/LoadMore'
import { SkeletonList } from '../components/Skeleton'
import DataError from '../components/DataError'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import { PageHeader } from '../ui'
import { storage } from '../firebase'
import { deleteStoredDocument, openStoredDocument, probeStorage, storageFailureMessage } from '../lib/generatedDocs'

const formatSize = (bytes) => (bytes >= 1024 * 1024
  ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
  : `${Math.max(1, Math.round(bytes / 1024))} KB`)

const formatDate = (timestamp) => (timestamp?.toDate
  ? timestamp.toDate().toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
  : '—')

/**
 * The member's document library (P3-3).
 *
 * Every file the portal generates — lesson plans, schemes, exam papers, quiz
 * decks, study notes — can be kept here instead of existing only as whatever
 * landed in the downloads folder. The file goes to Cloud Storage under
 * `generated/{uid}/…` and this page lists the records; `storage.rules` is what
 * makes the folder private.
 */
export default function DocumentLibrary() {
  const { user } = useAuth()
  const toast = useToast()
  const [pendingDelete, setPendingDelete] = useState(null)
  const [busy, setBusy] = useState(null)
  // `storage` being configured is not the same as the project having a bucket:
  // Cloud Storage needs the Blaze plan, so this page has three states and the
  // empty one must not be mistaken for "you have saved nothing yet".
  const [storageState, setStorageState] = useState('checking')

  useEffect(() => {
    if (!storage || !user) return undefined
    let active = true
    probeStorage().then((answer) => { if (active) setStorageState(answer) })
    return () => { active = false }
  }, [user])

  // Scoped to the caller on purpose: the read rule asks for the owner, and an
  // un-filtered list of this collection is denied for ordinary members.
  const {
    rows, loading, error, hasMore, loadingMore, loadMore, moreError,
  } = usePagedCollection('generated_documents', {
    filters: [['authorId', '==', user.uid]],
    sort: 'createdAt',
    pageSize: 24,
  })

  const open = async (record) => {
    setBusy(record.id)
    try {
      await openStoredDocument(record)
    } catch (error) {
      toast.error(storageFailureMessage(error))
    } finally {
      setBusy(null)
    }
  }

  const remove = async () => {
    try {
      await deleteStoredDocument(pendingDelete)
      toast.success(`${pendingDelete.name} deleted`)
    } catch (error) {
      toast.error(storageFailureMessage(error))
    } finally {
      setPendingDelete(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="My library"
        subtitle="Documents you generated, kept so you can open them again without rebuilding them. Only you can see this folder — they are stored under your own account."
      />

      {!storage && (
        <EmptyState
          title="The library is not available in this build"
          message="Firebase Storage is not configured, so documents can still be downloaded but not kept here."
        />
      )}

      {storage && error && <DataError what="your saved documents" error={error} />}
      {storage && loading && <SkeletonList rows={4} />}

      {storage && storageState === 'missing' && (
        <EmptyState
          title="The library needs Firebase Storage"
          message="This project has no Storage bucket — Cloud Storage requires a billing account, so the library is off. Exports still download to your computer, and turning Storage on later makes this page work with no change to the app."
          action={
            <a className="btn-secondary text-xs" href="https://console.firebase.google.com/" target="_blank" rel="noreferrer">
              Open the Firebase console
            </a>
          }
        />
      )}

      {storage && storageState !== 'missing' && !loading && !error && rows.length === 0 && (
        <EmptyState
          title="Nothing saved yet"
          message="Open a lesson plan, scheme, exam paper or quiz and press “Save to library” — it will be here next time."
        />
      )}

      {storage && rows.length > 0 && (
        <ul className="space-y-3">
          {rows.map((record) => (
            <li key={record.id} className="card flex flex-wrap items-center gap-4 p-4">
              <div className="min-w-0 flex-1">
                <p className="card-title truncate">{record.name}</p>
                <p className="card-meta mt-1 flex flex-wrap items-center gap-2">
                  <span className="chip-brand">{record.kindLabel || record.kind}</span>
                  {record.meta?.subjectName || record.meta?.subjectId
                    ? <span>{record.meta.subjectName || record.meta.subjectId}</span>
                    : null}
                  {record.meta?.grade ? <span>{record.meta.grade}</span> : null}
                  {record.meta?.term ? <span>Term {record.meta.term}</span> : null}
                  <span>{formatSize(record.bytes || 0)}</span>
                  <span>{formatDate(record.createdAt)}</span>
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => open(record)}
                  disabled={busy === record.id}
                >
                  {busy === record.id ? 'Opening…' : 'Open'}
                </button>
                <button type="button" className="btn-secondary" onClick={() => setPendingDelete(record)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {storage && <LoadMore hasMore={hasMore} loading={loadingMore} error={moreError} onLoad={loadMore} loaded={rows.length} />}

      <ConfirmModal
        open={Boolean(pendingDelete)}
        title="Delete this document?"
        message={pendingDelete ? `“${pendingDelete.name}” will be removed from your library. You can generate it again at any time.` : ''}
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
