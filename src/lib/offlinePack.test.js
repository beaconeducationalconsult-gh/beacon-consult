import { describe, expect, it, vi, afterEach } from 'vitest'
import { packFiles, warmPack, formatKb } from './offlinePack'

/*
 * Offline packs (P3-2). The unit under test is small on purpose: it decides
 * *what* a subject-grade needs and fetches it through the service worker. These
 * tests hold the file list to the paths the worker and the hooks actually use —
 * a renamed file here would mean a pack that reports success and caches nothing.
 */

afterEach(() => vi.unstubAllGlobals())

describe('what a pack contains', () => {
  it('asks for the grade files and this subject’s schedules file only', () => {
    const urls = packFiles('B4', 'mathematics').map((f) => f.url)
    expect(urls).toEqual([
      '/curriculum/grades.json',
      '/curriculum/b4_subjects.json',
      '/curriculum/b4_indicators.json',
      '/curriculum/b4_schemes.json',
      '/curriculum/schedules/b4-mathematics.json',
    ])
  })

  it('matches the path useSchedules() builds', () => {
    // The hook builds `schedules/<grade>-<subject>.json`; a pack for another
    // subject must not collide with it.
    const [schedule] = packFiles('B9', 'career-technology').slice(-1)
    expect(schedule.url).toBe('/curriculum/schedules/b9-career-technology.json')
  })

  it('accepts a lower-case grade, because URLs are typed by hand', () => {
    expect(packFiles('b7', 'science').map((f) => f.url)).toContain('/curriculum/b7_indicators.json')
  })
})

describe('fetching a pack', () => {
  const files = packFiles('B1', 'mathematics')

  it('reports progress and a size, and reloads rather than reusing the HTTP cache', async () => {
    const seen = []
    const fetchMock = vi.fn(async (url, options) => {
      seen.push([url, options.cache])
      return { ok: true, status: 200, blob: async () => ({ size: 2048 }) }
    })
    vi.stubGlobal('fetch', fetchMock)

    const progress = []
    const result = await warmPack(files, { onProgress: (p) => progress.push(p) })

    expect(result).toMatchObject({ files: files.length, downloaded: files.length, complete: true })
    expect(result.bytes).toBe(files.length * 2048)
    expect(progress).toHaveLength(files.length)
    expect(progress.at(-1).done).toBe(progress.at(-1).total)
    // Every request carried cache: 'reload' — a pack that quietly kept an old
    // file would be worse than no pack.
    expect(seen.every(([, cache]) => cache === 'reload')).toBe(true)
    expect(seen.map(([url]) => url)).toEqual(files.map((f) => f.url))
  })

  it('collects what failed instead of throwing, and says so', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url) =>
      url.includes('schedules')
        ? { ok: false, status: 404, blob: async () => ({ size: 0 }) }
        : { ok: true, status: 200, blob: async () => ({ size: 1024 }) }))

    const result = await warmPack(files)
    expect(result.complete).toBe(false)
    expect(result.downloaded).toBe(files.length - 1)
    expect(result.missing).toHaveLength(1)
    expect(result.missing[0].url).toContain('schedules/b1-mathematics.json')
  })

  it('treats a thrown network error the same way', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new Error('offline')
    }))
    const result = await warmPack(files)
    expect(result.downloaded).toBe(0)
    expect(result.missing.every((m) => m.error === 'offline')).toBe(true)
  })

  it('formats a size a teacher can read', () => {
    expect(formatKb(0)).toBe('1 KB')
    expect(formatKb(2048)).toBe('2 KB')
    expect(formatKb(5 * 1024 * 1024)).toBe('5120 KB')
  })
})
