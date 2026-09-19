/*
 * Offline packs (P3-2): pull every bundle file a subject-grade needs into the
 * service worker's cache, deliberately and with a progress count.
 *
 * Nothing here writes to Cache Storage directly. The files are fetched through
 * the normal `fetch`, which the service worker already intercepts and caches
 * stale-while-revalidate — so an explicit warm-up puts exactly the same entries
 * in exactly the same place a teacher's browsing would have, without the app
 * having to know the worker's cache name (it is named after the bundle hash, see
 * `public/sw.js`). In dev, where there is no worker, the fetches still succeed;
 * they simply do not persist.
 */

const BASE_URL = import.meta.env.BASE_URL || '/'

/** The files a subject-grade needs to be readable and plannable offline. */
export function packFiles(grade, subjectId) {
  const g = String(grade || '').toLowerCase()
  return [
    { path: 'curriculum/grades.json', label: 'Grade list', weight: 1 },
    { path: `curriculum/${g}_subjects.json`, label: 'Subjects', weight: 1 },
    { path: `curriculum/${g}_indicators.json`, label: 'Indicators', weight: 2 },
    { path: `curriculum/${g}_schemes.json`, label: 'Schemes of learning', weight: 2 },
    { path: `curriculum/schedules/${g}-${subjectId}.json`, label: 'Scheduled lessons', weight: 3 },
  ].map((file) => ({ ...file, url: `${BASE_URL}${file.path}` }))
}

const formatKb = (bytes) => `${Math.max(1, Math.round(bytes / 1024))} KB`

/**
 * Fetch every file of a pack, reporting progress as it goes.
 *
 * `cache: 'reload'` skips the browser's HTTP cache so the service worker sees a
 * real network response and stores the current copy — a pack that silently kept
 * a month-old file would be worse than no pack. Individual failures are
 * collected, not thrown: a subject with no schedule file is normal, and the
 * caller shows what did not come down.
 */
export async function warmPack(files, { onProgress } = {}) {
  const total = files.reduce((sum, file) => sum + (file.weight || 1), 0)
  let done = 0
  let bytes = 0
  const missing = []

  for (const file of files) {
    try {
      const response = await fetch(file.url, { cache: 'reload' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const body = await response.blob()
      bytes += body.size
      done += file.weight || 1
      onProgress?.({ file, done, total, bytes, ok: true })
    } catch (error) {
      done += file.weight || 1
      missing.push({ ...file, error: error.message })
      onProgress?.({ file, done, total, bytes, ok: false, error })
    }
  }

  return {
    files: files.length,
    downloaded: files.length - missing.length,
    missing,
    bytes,
    size: formatKb(bytes),
    complete: missing.length === 0,
  }
}

export { formatKb }
