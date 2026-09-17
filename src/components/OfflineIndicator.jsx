import { useEffect, useState } from 'react'
import { waitForPendingWrites } from 'firebase/firestore'
import { db } from '../firebase'

/**
 * Bottom-centre pill: offline / syncing / synced.
 * Driven by the browser's online events plus Firestore's pending-write queue,
 * so a member knows their work is safe before they lose signal.
 */
export default function OfflineIndicator() {
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

  if (online && !syncing && !justSynced) return null

  const [tone, text] = !online
    ? ['bg-slate-800', 'Offline — changes save on this device and sync later']
    : syncing
      ? ['bg-brand-600', 'Syncing your changes…']
      : ['bg-emerald-600', 'All changes synced']

  return (
    <div className="pointer-events-none fixed bottom-4 left-1/2 z-40 -translate-x-1/2 px-4" role="status" aria-live="polite">
      <div className={`rounded-full px-4 py-2 text-xs font-medium text-white shadow-lg ${tone}`}>{text}</div>
    </div>
  )
}
