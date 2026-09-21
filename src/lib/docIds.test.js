import { describe, expect, it } from 'vitest'
import { indicatorDocId } from './docIds'

describe('indicatorDocId', () => {
  it('is stable: the same author and indicator always give the same id', () => {
    expect(indicatorDocId('u1', 'mathematics', 'B4.1.1.1.1'))
      .toBe(indicatorDocId('u1', 'mathematics', 'B4.1.1.1.1'))
  })

  it('scopes the indicator to its subject, because the code alone is not unique', () => {
    // B4.1.1.1.1 is in every B4 subject: without the subject these two teachers'
    // plans would be one document
    expect(indicatorDocId('u1', 'mathematics', 'B4.1.1.1.1'))
      .not.toBe(indicatorDocId('u1', 'science', 'B4.1.1.1.1'))
  })

  it('separates authors and grades', () => {
    expect(indicatorDocId('u1', 'mathematics', 'B4.1.1.1.1'))
      .not.toBe(indicatorDocId('u2', 'mathematics', 'B4.1.1.1.1'))
    expect(indicatorDocId('u1', 'mathematics', 'B4.1.1.1.1'))
      .not.toBe(indicatorDocId('u1', 'mathematics', 'B5.1.1.1.1'))
  })

  it('sanitises what it is given, so the id is safe as a path segment', () => {
    const id = indicatorDocId('u 1', 'our world/our people', 'B4.1.1.1.1')
    expect(id).not.toMatch(/[^\w.-]/)
    expect(id).toBe('u_1_our_world_our_people_B4.1.1.1.1')
  })

  it('tolerates a missing part without throwing', () => {
    expect(indicatorDocId('u1', undefined, 'B4.1.1.1.1')).toBe('u1__B4.1.1.1.1')
  })
})
