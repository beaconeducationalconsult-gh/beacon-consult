import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { storage } from '../firebase'
import { saveGeneratedDocument } from '../lib/generatedDocs'

/**
 * "Save this generated document to my library" (P3-3), for any page that
 * produces a file.
 *
 * The page passes a *function* that returns the file's Blob, not the Blob
 * itself: building a document is not free, and a teacher who never presses the
 * button should never pay for it. Failures are reported where the work happened
 * — the download the teacher already has is unaffected either way.
 *
 * `available` is false in a build with no Firebase config, or for a signed-out
 * visitor, so a page can hide the button rather than offer a dead one.
 */
export function useLibrarySave() {
  const { user } = useAuth()
  const toast = useToast()
  const [saving, setSaving] = useState(false)

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
      toast.error(`Could not save to your library: ${error?.code || error.message}`)
      return null
    } finally {
      setSaving(false)
    }
  }

  return { save, saving, available: Boolean(storage && user) }
}
