import { describe, expect, it } from 'vitest'
import { FIREBASE_ENV_BLOCK } from './firebaseConfigSource'
import { buildInfoUrl, isLocalHost, setupNoticeCopy, setupNoticeMode } from './setupGuidance'

/*
 * The setup notice is the first thing a deployment shows when its build had no
 * Firebase config, and it has to send two different readers to two different
 * fixes: `.env.local` and a restart on a laptop, environment variables and a
 * **re-deploy** on Vercel. The first real deploy (2026-09-20) was built without
 * any of the six values, and the screen told the person looking at the live URL
 * to `cp .env.example .env.local` — a file that is nowhere near that problem.
 *
 * `src/lib/firebaseConfigSource.js` owns the names, the paste block and what
 * counts as missing; this file is only the words a reader sees.
 */

/** The first deploy step's code — the committed config, which needs no dashboard. */
const COMMITTED_STEP_CODE = 'src/firebaseConfig.js\n  apiKey: …\n  projectId: …'
const DEPLOY = { mode: 'deploy', missing: ['VITE_FIREBASE_API_KEY', 'VITE_FIREBASE_APP_ID'], origin: 'https://beacon-edu-consult.vercel.app' }
const LOCAL = { mode: 'local', missing: ['VITE_FIREBASE_API_KEY'] }

describe('isLocalHost / setupNoticeMode', () => {
  it('recognises the ways a localhost URL is spelled', () => {
    for (const host of ['localhost', 'LOCALHOST', '127.0.0.1', '[::1]', '0.0.0.0', 'app.localhost', '5199-abc.e2b.app']) {
      expect(isLocalHost(host), host).toBe(true)
    }
    for (const host of ['beacon-edu-consult.vercel.app', 'notlocalhost.com', '192.168.1.20', '']) {
      expect(isLocalHost(host), host).toBe(false)
    }
  })

  it('treats a production build on localhost as local', () => {
    // `yarn build && yarn preview` — the production bundle, on the machine that
    // built it. Sending that reader to Vercel settings would be the mirror of
    // the bug this file exists for.
    expect(setupNoticeMode({ prod: true, hostname: 'localhost' })).toBe('local')
  })

  it('treats a sandbox preview build as local, not as a deploy', () => {
    // `yarn preview` behind a generated sandbox hostname: production build, but
    // the person looking at it has the repo — don't send them to Vercel.
    expect(setupNoticeMode({ prod: true, hostname: '5199-abc123.e2b.app' })).toBe('local')
  })

  it('treats a dev server as local wherever it is reachable', () => {
    expect(setupNoticeMode({ prod: false, hostname: 'beacon-edu-consult.vercel.app' })).toBe('local')
  })

  it('treats a production build on a real domain as a deploy', () => {
    expect(setupNoticeMode({ prod: true, hostname: 'beacon-edu-consult.vercel.app' })).toBe('deploy')
  })
})

describe('buildInfoUrl', () => {
  it('appends the path to an origin, with or without a trailing slash', () => {
    expect(buildInfoUrl('https://example.com')).toBe('https://example.com/build-info.json')
    expect(buildInfoUrl('https://example.com/')).toBe('https://example.com/build-info.json')
  })
})

describe('setupNoticeCopy in deploy mode', () => {
  const copy = setupNoticeCopy(DEPLOY)
  const text = [copy.title, copy.lead, copy.note, copy.footnote, ...copy.steps.flatMap((s) => [s.title, s.code])].join('\n')

  it('sends the reader to Vercel and names the environments', () => {
    expect(text).toContain('Settings → Environment Variables')
    expect(text).toContain('Production')
    expect(text).toContain('Preview')
  })

  it('says a variable change is not enough — the deploy has to run again', () => {
    expect(text).toContain('Redeploy')
    expect(text).toContain('does not rebuild anything by itself')
  })

  it('lists exactly the values this build was missing', () => {
    const missingStep = copy.steps.find((s) => s.code === DEPLOY.missing.join('\n'))
    expect(missingStep, 'a step carries the missing names').toBeTruthy()
    expect(missingStep.code).not.toContain('VITE_FIREBASE_PROJECT_ID')
  })

  it('names the committed config as the fix that needs no dashboard', () => {
    expect(text).toContain('src/firebaseConfig.js')
    expect(copy.steps[0].code).toContain('src/firebaseConfig.js')
  })

  it('gives a check that needs no app: /build-info.json on this deploy', () => {
    expect(text).toContain('https://beacon-edu-consult.vercel.app/build-info.json')
    expect(text).toContain('firebaseConfigured')
  })

  it('never tells a deployed build to copy .env.local or run yarn dev', () => {
    expect(copy.lead).toContain('is not part of a deploy')
    for (const step of copy.steps) {
      expect(step.code || '').not.toContain('cp .env.example')
      expect(step.code || '').not.toContain('yarn dev')
    }
  })

  it('does not print an empty list when nothing is missing', () => {
    // The "this build was compiled without: …" step carries the names; with
    // none to carry it must not appear as an empty block.
    const noMissing = setupNoticeCopy({ mode: 'deploy', origin: 'https://example.com', missing: [] })
    const codes = noMissing.steps.map((s) => s.code).filter(Boolean)
    expect(codes).toEqual([COMMITTED_STEP_CODE, FIREBASE_ENV_BLOCK, buildInfoUrl('https://example.com')])
    expect(codes.some((c) => c.trim() === '')).toBe(false)
  })

  it('keeps the reassurance about the curriculum', () => {
    expect(copy.curriculum.body).toContain('44 files, 11 grades, 4,040 indicators')
  })
})

describe('setupNoticeCopy in local mode', () => {
  const copy = setupNoticeCopy(LOCAL)
  const text = [copy.lead, copy.footnote, ...copy.steps.flatMap((s) => [s.title, s.code])].join('\n')

  it('gives the file to copy, the values, and the restart', () => {
    expect(text).toContain('cp .env.example .env.local')
    expect(text).toContain('Restart the dev server')
    expect(text).toContain('yarn dev')
  })

  it('does not send a local build to Vercel', () => {
    expect(text).not.toContain('Redeploy')
    expect(text).not.toContain('/build-info.json')
  })

  it('surfaces which values were not found', () => {
    expect(copy.missing).toEqual(LOCAL.missing)
  })
})
