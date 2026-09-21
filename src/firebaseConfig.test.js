import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { firebaseConfig } from './firebaseConfig'
import { FIREBASE_ENV_NAMES } from './lib/firebaseConfigSource'

/*
 * The committed config every build falls back to.
 *
 * This file is what makes a deploy work with no environment at all, so it has to
 * be *right*: a typo here is a deploy that boots into the setup notice with a
 * green build, which is the failure this whole mechanism exists to end. The
 * checks below are about shape and provenance — nothing here needs the network,
 * and nothing here reads the values out loud.
 */

const ENTRIES = Object.entries(FIREBASE_ENV_NAMES)

describe('the committed Firebase config', () => {
  it('names all six values and nothing else', () => {
    expect(Object.keys(firebaseConfig)).toEqual(Object.keys(FIREBASE_ENV_NAMES))
  })

  it('has a non-blank value for every one of them', () => {
    for (const [key, envName] of ENTRIES) {
      expect(String(firebaseConfig[key] ?? '').trim(), `${key} (${envName}) is empty`).not.toBe('')
    }
  })

  it('carries no BOM, newline or stray whitespace in a value', () => {
    // The failure that motivated the file: PowerShell's `Set-Content -Encoding
    // utf8` wrote a BOM, Vite's parser did not strip it, and the API key's line
    // vanished while the rest of the file loaded — the file *looked* complete.
    for (const [key, value] of Object.entries(firebaseConfig)) {
      expect(value, `${key} has surrounding whitespace`).toBe(value.trim())
      expect(/[\uFEFF\r\n\t]/.test(value), `${key} contains a BOM or control character`).toBe(false)
    }
  })

  it('points at the same Firebase project as .firebaserc', () => {
    // Two files, one project: a config pointing somewhere else gets every rule
    // and index deployed to a database the app never talks to.
    const rc = JSON.parse(readFileSync(resolve(process.cwd(), '.firebaserc'), 'utf8'))
    const projectId = rc.projects?.default
    expect(projectId).toBeTruthy()
    expect(firebaseConfig.projectId).toBe(projectId)
  })

  it('looks like a Firebase web config, not a copy-paste of something else', () => {
    expect(firebaseConfig.apiKey).toMatch(/^AIza[0-9A-Za-z_-]{30,}$/)
    expect(firebaseConfig.authDomain).toBe(`${firebaseConfig.projectId}.firebaseapp.com`)
    expect(firebaseConfig.appId).toMatch(/^1:\d+:web:[0-9a-f]+$/)
    expect(firebaseConfig.messagingSenderId).toMatch(/^\d+$/)
    // The sender id inside the app id is the same Google project as the sender id.
    expect(firebaseConfig.appId.split(':')[1]).toBe(firebaseConfig.messagingSenderId)
    expect(firebaseConfig.storageBucket).toMatch(/^(?:.+\.(?:firebasestorage\.app|appspot\.com))$/)
  })
})
