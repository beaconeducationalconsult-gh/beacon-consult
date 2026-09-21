import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  FIREBASE_ENV_BLOCK,
  FIREBASE_ENV_LIST,
  FIREBASE_ENV_NAMES,
  missingEnvNames,
  resolveFirebaseConfig,
} from './firebaseConfigSource'

/*
 * Where the six Firebase values come from, and the rule that decides it.
 *
 * The rule exists because of two real deploys: the first had no config at all,
 * and the second had `.env.production` committed and *still* shipped with none,
 * because (a) a BOM from Windows PowerShell hugged the first line — Vite's env
 * parser does not strip it, so that value silently vanished, and the build only
 * looked healthy locally because `.env.local` happened to supply that one key —
 * and (b) Vite lets `process.env` win over `.env` files, so a variable that
 * exists in Vercel but is *blank* empties out a value the repository supplies.
 *
 * So: a non-blank environment value wins, anything blank falls back to the
 * committed `src/firebaseConfig.js`, and blank-but-present is reported by name.
 */

const COMMITTED = {
  apiKey: 'committed-key',
  authDomain: 'committed.firebaseapp.com',
  projectId: 'committed-project',
  storageBucket: 'committed-project.firebasestorage.app',
  messagingSenderId: '123456789012',
  appId: '1:123456789012:web:abcdef',
}

describe('the six names', () => {
  it('are written down once, in .env.example order', () => {
    const example = readFileSync(resolve(process.cwd(), '.env.example'), 'utf8')
    const names = example
      .split('\n')
      .filter((line) => line.startsWith('VITE_'))
      .map((line) => line.split('=')[0].trim())
    expect(names).toEqual(FIREBASE_ENV_LIST)
  })

  it('print one line per value in the paste block', () => {
    expect(FIREBASE_ENV_BLOCK.split('\n')).toEqual(FIREBASE_ENV_LIST.map((name) => `${name}=…`))
  })

  it('cover every value src/firebase.js reads from import.meta.env', () => {
    // The env reads in firebase.js must stay literal for Vite to replace them at
    // build time, so the only guard against a seventh value being added there
    // without a name here is this scan of the source.
    const source = readFileSync(resolve(process.cwd(), 'src/firebase.js'), 'utf8')
    const block = source.split('const envFirebaseConfig = {')[1].split('}')[0]
    const keys = [...block.matchAll(/^\s*(\w+):\s*import\.meta\.env\.(\w+)/gm)].map((m) => [m[1], m[2]])
    expect(keys).toEqual(Object.entries(FIREBASE_ENV_NAMES))
  })
})

describe('missingEnvNames', () => {
  it('reports all six for an empty config', () => {
    expect(missingEnvNames({})).toEqual(FIREBASE_ENV_LIST)
  })

  it('treats empty and whitespace-only values as missing', () => {
    expect(missingEnvNames({ apiKey: '', projectId: '   ' })).toEqual(FIREBASE_ENV_LIST)
  })

  it('leaves out the values that are set', () => {
    expect(missingEnvNames({ apiKey: 'AIza-not-a-real-key', projectId: 'beacon-edu-consult-proj' })).toEqual([
      'VITE_FIREBASE_AUTH_DOMAIN',
      'VITE_FIREBASE_STORAGE_BUCKET',
      'VITE_FIREBASE_MESSAGING_SENDER_ID',
      'VITE_FIREBASE_APP_ID',
    ])
  })
})

describe('resolveFirebaseConfig', () => {
  it('uses the committed values when the environment has none', () => {
    const { config, missing, source, fromCommitted } = resolveFirebaseConfig({ env: {}, committed: COMMITTED })
    expect(config).toEqual(COMMITTED)
    expect(missing).toEqual([])
    expect(source).toBe('committed')
    expect(fromCommitted).toEqual(FIREBASE_ENV_LIST)
  })

  it('lets a non-blank environment value win, so a deploy can point elsewhere', () => {
    const env = { VITE_FIREBASE_PROJECT_ID: 'other-project' }
    const { config, source, fromEnv, fromCommitted } = resolveFirebaseConfig({ env, committed: COMMITTED })
    expect(config.projectId).toBe('other-project')
    expect(config.apiKey).toBe('committed-key')
    expect(source).toBe('mixed')
    expect(fromEnv).toEqual(['VITE_FIREBASE_PROJECT_ID'])
    expect(fromCommitted).not.toContain('VITE_FIREBASE_PROJECT_ID')
  })

  it('falls back past a value that is present but blank, and names it', () => {
    // The second deploy's failure: the variable existed, so the dashboard and
    // `vercel env ls` both looked configured, while Vite gave the bundle ''.
    const env = { VITE_FIREBASE_API_KEY: '', VITE_FIREBASE_APP_ID: '   ' }
    const { config, missing, envBlankNames } = resolveFirebaseConfig({ env, committed: COMMITTED })
    expect(config.apiKey).toBe('committed-key')
    expect(config.appId).toBe('1:123456789012:web:abcdef')
    expect(missing).toEqual([])
    expect(envBlankNames).toEqual(['VITE_FIREBASE_API_KEY', 'VITE_FIREBASE_APP_ID'])
  })

  it('does not name a variable that was never set', () => {
    const { envBlankNames } = resolveFirebaseConfig({ env: {}, committed: COMMITTED })
    expect(envBlankNames).toEqual([])
  })

  it('reports what is still missing when neither side has a value', () => {
    const { config, missing, source } = resolveFirebaseConfig({ env: {}, committed: { apiKey: 'only-key' } })
    expect(config.projectId).toBe('')
    expect(missing).toContain('VITE_FIREBASE_PROJECT_ID')
    expect(missing).toContain('VITE_FIREBASE_APP_ID')
    expect(missing).not.toContain('VITE_FIREBASE_API_KEY')
    expect(source).toBe('committed')
  })

  it('trims the values it hands to the app', () => {
    const { config } = resolveFirebaseConfig({ env: { VITE_FIREBASE_PROJECT_ID: '  spaced-project  ' } })
    expect(config.projectId).toBe('spaced-project')
  })

  it('returns a complete, empty config for no arguments at all', () => {
    const { config, missing, source } = resolveFirebaseConfig()
    expect(Object.keys(config)).toEqual(Object.keys(FIREBASE_ENV_NAMES))
    expect(Object.values(config).every((v) => v === '')).toBe(true)
    expect(missing).toEqual(FIREBASE_ENV_LIST)
    expect(source).toBe('committed')
  })
})
