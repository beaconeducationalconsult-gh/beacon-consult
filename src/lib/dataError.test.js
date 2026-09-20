import { describe, expect, it } from 'vitest'
import { dataErrorMessage, indexUrlFrom } from './dataError'

/*
 * The four failures a member (or whoever is running the deploy) actually meets,
 * and the one piece of machinery in them: the index link Firestore puts in a
 * `failed-precondition` message is the fastest fix for a missing index, and it
 * used to be thrown away.
 */

describe('dataErrorMessage', () => {
  it('names the account, not the deploy, for permission-denied', () => {
    const { code, cause, hint, link } = dataErrorMessage({ code: 'permission-denied' }, 'the question bank')
    expect(code).toBe('permission-denied')
    expect(cause).toContain('the question bank')
    expect(cause).toContain('approves it')
    // The second cause is the one that wastes an afternoon: rules newer than the build.
    expect(hint).toContain('re-publish firestore.rules')
    expect(link).toBeNull()
  })

  it('turns a missing index into a link that creates it', () => {
    const error = {
      code: 'failed-precondition',
      message: 'The query requires an index. You can create it here: '
        + 'https://console.firebase.google.com/v1/r/project/beacon-edu-consult-proj/firestore/indexes?create_composite=Ck8a',
    }
    const { link, cause, hint } = dataErrorMessage(error, 'your documents')
    expect(link.href).toBe('https://console.firebase.google.com/v1/r/project/beacon-edu-consult-proj/firestore/indexes?create_composite=Ck8a')
    expect(link.label).toMatch(/index/i)
    expect(cause).toContain('your documents')
    expect(hint).toContain('Create index')
  })

  it('still says what to do when the error carries no link', () => {
    const { link, hint } = dataErrorMessage({ code: 'failed-precondition', message: 'no url here' })
    expect(link).toBeNull()
    expect(hint).toContain('firestore.indexes.json')
    expect(hint).toContain('firestore:indexes')
  })

  it('separates "offline" from "broken"', () => {
    const { cause, hint, link } = dataErrorMessage({ code: 'unavailable' }, 'the schemes list')
    expect(cause).toContain('the schemes list')
    expect(hint).toContain('offline')
    expect(link).toBeNull()
  })

  it('always returns something usable, even with no error object', () => {
    for (const error of [undefined, null, {}, { code: 'internal' }, new Error('boom')]) {
      const { code, cause, hint } = dataErrorMessage(error)
      expect(code).toBeTruthy()
      expect(cause.length).toBeGreaterThan(20)
      expect(hint.length).toBeGreaterThan(20)
    }
  })

  it('names signing in again when the session expired', () => {
    expect(dataErrorMessage({ code: 'unauthenticated' }, 'the members list').hint).toContain('Sign in again')
  })
})

describe('indexUrlFrom', () => {
  it('strips the punctuation the SDK leaves on the end', () => {
    expect(indexUrlFrom({ message: 'create it here: https://console.firebase.google.com/v1/r/x.' }))
      .toBe('https://console.firebase.google.com/v1/r/x')
    expect(indexUrlFrom({ message: 'see (https://console.firebase.google.com/v1/r/y)' }))
      .toBe('https://console.firebase.google.com/v1/r/y')
  })

  it('is null for anything else — including our own SPA error pages', () => {
    expect(indexUrlFrom({ message: 'permission denied' })).toBeNull()
    expect(indexUrlFrom({ message: 'https://beacon.example.com/portal/questions' })).toBeNull()
    expect(indexUrlFrom({})).toBeNull()
    expect(indexUrlFrom(undefined)).toBeNull()
  })
})
