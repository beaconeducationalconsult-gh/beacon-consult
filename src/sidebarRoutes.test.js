import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

/*
 * The sidebar and the router have to agree.
 *
 * A `to:` that no route answers is the cheapest bug in the app to ship and the
 * most annoying to find — the link renders, the page is blank, and nothing
 * fails the build. The exam builder (P1-5's paper half) is reached from the
 * sidebar *and* from the bank, so this guard lands with it.
 *
 * It reads the two files as text rather than rendering them: the portal needs
 * Firebase to render at all, and the contract being checked (a link names a
 * route) is visible in the source.
 */

const read = (path) => readFileSync(new URL(`./${path}`, import.meta.url), 'utf8')

const app = read('App.jsx')
const sidebar = read('components/Sidebar.jsx')

/** Every `<Route path="…" element={<Page />} />`, direct children resolved below. */
function routePaths(source) {
  const paths = []
  const re = /<Route\s+path="([^"]+)"/g
  let match
  while ((match = re.exec(source)) !== null) paths.push(match[1])
  return paths
}

/**
 * The portal's nested paths, as the browser sees them.
 *
 * Includes `/portal` itself: the index route is written `<Route index
 * element={<Workspace />} />`, which has no `path` to read, and the sidebar's
 * first link goes exactly there.
 */
function portalUrls() {
  const portal = app.slice(app.indexOf('<Route path="/portal"'))
  const urls = routePaths(portal)
    .filter((path) => !path.startsWith('/') && path !== '*')
    .map((path) => `/portal/${path}`)
  if (/<Route\s+index/.test(portal)) urls.push('/portal')
  return urls
}

describe('the sidebar links where the router listens', () => {
  const urls = new Set(portalUrls())
  const links = [...sidebar.matchAll(/to:\s*'([^']+)'/g)]
    .map((match) => match[1])
    .filter((to) => to.startsWith('/portal'))

  it('finds the portal routes and the portal links', () => {
    expect(urls.size).toBeGreaterThan(20)
    expect(links.length).toBeGreaterThan(10)
  })

  it('has a route for every sidebar link', () => {
    for (const to of links) {
      // `/portal/authors/:authorId` link targets have a parameter; the router
      // declares it too, so the comparison is on the pattern, not a real id.
      expect(urls.has(to), `Sidebar links to ${to}, which no route declares`).toBe(true)
    }
  })

  it('routes every page the sidebar and the bank point at', () => {
    // The exam builder is the one this guard was written for: a sidebar entry,
    // a link from the bank, and a lazy import that must exist.
    expect(urls.has('/portal/questions/exam')).toBe(true)
    expect(app).toMatch(/lazy\(\(\) => import\('\.\/pages\/ExamBuilder'\)\)/)
    expect(read('pages/ExamBuilder.jsx')).toContain('buildQuestionPaper(')
  })
})
