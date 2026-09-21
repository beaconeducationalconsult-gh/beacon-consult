import { useEffect, useState } from 'react'
import { waitForPendingWrites } from 'firebase/firestore'
import { db } from '../firebase'
import { cn } from '../ui/cn'

/**
 * Compact connection/sync status dot for the top bar: online / syncing / synced
 * / offline. Driven by the browser's online events plus Firestore's
 * pending-write queue, so a member knows their work is safe before they lose
 * signal. The readable state is exposed via `title` and an `aria-live` region.
 */
export default function OfflineIndicator({ className }) {
  const [online, setOnline] = useState(navigator.onLine)
  const [syncing, setSyncing] = useState(false)
  const [justSynced, setJustSynced] = useState(false)

  useEffect(() => {
    const goOnline = async () => {
      setOnline(true)
      setSyncing(true)
      try {
        await waitForPendingWrites(db)
        setJustSynced(true)
        setTimeout(() => setJustSynced(false), 2500)
      } catch {
        /* ignore — the next write attempt will surface real errors */
      } finally {
        setSyncing(false)
      }
    }
    const goOffline = () => setOnline(false)

    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  const status = !online
    ? { dot: 'bg-danger-500', label: 'Offline — changes save on this device and sync later' }
    : syncing
      ? { dot: 'bg-warning-500 animate-pulse', label: 'Syncing your changes…' }
      : justSynced
        ? { dot: 'bg-success-500', label: 'All changes synced' }
        : { dot: 'bg-success-500', label: 'Online' }

  return (
    <span className={cn('inline-flex items-center', className)} title={status.label}>
      <span className={cn('h-2.5 w-2.5 rounded-full', status.dot)} aria-hidden="true" />
      <span className="sr-only" role="status" aria-live="polite">
        {status.label}
      </span>
    </span>
  )
}
