import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { storage } from '../firebase'
import { probeStorage, saveGeneratedDocument, storageFailureMessage } from '../lib/generatedDocs'

/**
 * "Save this generated document to my library" (P3-3), for any page that
 * produces a file.
 *
 * The page passes a *function* that returns the file's Blob, not the Blob
 * itself: building a document is not free, and a teacher who never presses the
 * button should never pay for it. Failures are reported where the work happened
 * — the download the teacher already has is unaffected either way.
 *
 * `available` is false in a build with no Firebase config, for a signed-out
 * visitor, **and on a project with no Storage bucket** — Cloud Storage needs the
 * Blaze plan, so a school can be running everything else and no library. That
 * last case is why `missing` exists: a page renders the reason instead of a
 * button that could only fail. See `docs/build-deploy.md`.
 */
export function useLibrarySave() {
  const { user } = useAuth()
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [storageState, setStorageState] = useState('checking')

  useEffect(() => {
    // Nothing is set synchronously: the probe's answer drives the flag, and a
    // build with no config never starts one.
    if (!storage || !user) return undefined
    let active = true
    probeStorage().then((answer) => {
      if (active) setStorageState(answer)
    })
    return () => { active = false }
  }, [user])

  const missing = storageState === 'missing'

  const save = async (buildBlob, { kind, filename, meta }) => {
    if (!user) {
      toast.error('Sign in to keep documents in your library.')
      return null
    }
    setSaving(true)
    try {
      const blob = await buildBlob()
      const record = await saveGeneratedDocument({ blob, filename, kind, meta, user })
      toast.success(`${record.name} saved to your library`)
      return record
    } catch (error) {
      const message = storageFailureMessage(error)
      // A project with no bucket will answer the same way every time: remember
      // it so the button is replaced by the reason rather than retried.
      if (storageState !== 'missing' && /no Firebase Storage bucket/.test(message)) {
        setStorageState('missing')
      }
      toast.error(message)
      return null
    } finally {
      setSaving(false)
    }
  }

  return {
    save,
    saving,
    available: Boolean(storage && user) && !missing,
    missing: Boolean(storage && user) && missing,
  }
}
