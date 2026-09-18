import { describe, expect, it } from 'vitest'
import { buildTree } from './useCurriculum'

const ind = (over = {}) => ({
  id: 'x',
  code: 'B4.1.1.1.1',
  subjectId: 'mathematics',
  strandName: 'Number',
  strandNumber: 1,
  subStrandName: 'Counting',
  subStrandNumber: 1,
  contentStandardCode: 'B4.1.1.1',
  contentStandardDescription: 'Standard one',
  description: 'Do the thing',
  ...over,
})

const flatten = (tree) =>
  tree.flatMap((s) => s.subStrands.flatMap((sub) => sub.standards.flatMap((std) => std.indicators)))

describe('buildTree', () => {
  it('nests strand → sub-strand → content standard → indicators', () => {
    const tree = buildTree([ind(), ind({ id: 'y', code: 'B4.1.1.1.2' })], 'mathematics')

    expect(tree).toHaveLength(1)
    expect(tree[0].subStrands).toHaveLength(1)
    expect(tree[0].subStrands[0].standards).toHaveLength(1)
    expect(tree[0].subStrands[0].standards[0].indicators).toHaveLength(2)
    expect(tree[0].subStrands[0].standards[0].code).toBe('B4.1.1.1')
  })

  it('keeps only the requested subject', () => {
    const rows = [ind(), ind({ id: 'z', subjectId: 'science', strandName: 'Diversity' })]
    const tree = buildTree(rows, 'mathematics')

    expect(tree).toHaveLength(1)
    expect(flatten(tree).map((i) => i.id)).toEqual(['x'])
  })

  it('returns every subject when no subjectId is given', () => {
    const rows = [ind(), ind({ id: 'z', subjectId: 'science', strandName: 'Diversity' })]
    expect(flatten(buildTree(rows)).map((i) => i.id)).toEqual(['x', 'z'])
  })

  it('loses no indicator and duplicates none', () => {
    const rows = [
      ind({ id: 'a', strandNumber: 2, subStrandNumber: 1, contentStandardCode: 'B4.2.1.1' }),
      ind({ id: 'b', strandNumber: 1, subStrandNumber: 2, contentStandardCode: 'B4.1.2.1' }),
      ind({ id: 'c', strandNumber: 1, subStrandNumber: 1, contentStandardCode: 'B4.1.1.1' }),
      ind({ id: 'd', strandNumber: 1, subStrandNumber: 1, contentStandardCode: 'B4.1.1.2' }),
    ]
    const got = flatten(buildTree(rows, 'mathematics')).map((i) => i.id)
    expect(got.sort()).toEqual(['a', 'b', 'c', 'd'])
  })

  // Strands are keyed by name, so distinct rows need distinct names here.
  it('orders strands and sub-strands numerically, not as strings', () => {
    const rows = [
      ind({ id: 'ten', strandName: 'Ten', strandNumber: 10, subStrandName: 'A', subStrandNumber: 1 }),
      ind({ id: 'two', strandName: 'Two', strandNumber: 2, subStrandName: 'B', subStrandNumber: 2 }),
      ind({ id: 'one', strandName: 'One', strandNumber: 1, subStrandName: 'C', subStrandNumber: 10 }),
    ]
    const tree = buildTree(rows, 'mathematics')
    expect(tree.map((s) => s.number)).toEqual([1, 2, 10])
    expect(tree[2].subStrands.map((s) => s.number)).toEqual([1])
  })

  it('groups by strand name, so rows sharing a name share a strand', () => {
    const rows = [
      ind({ id: 'a', strandName: 'Number', strandNumber: 1 }),
      ind({ id: 'b', strandName: 'Number', strandNumber: 1, subStrandName: 'Other' }),
    ]
    const tree = buildTree(rows, 'mathematics')
    expect(tree).toHaveLength(1)
    expect(tree[0].subStrands).toHaveLength(2)
  })

  it('orders content standards by code', () => {
    const rows = [
      ind({ id: 'b', contentStandardCode: 'B4.1.1.2' }),
      ind({ id: 'a', contentStandardCode: 'B4.1.1.1' }),
    ]
    const standards = buildTree(rows, 'mathematics')[0].subStrands[0].standards
    expect(standards.map((s) => s.code)).toEqual(['B4.1.1.1', 'B4.1.1.2'])
  })

  it('falls back to placeholders when the hierarchy is unnamed', () => {
    const tree = buildTree(
      [ind({ strandName: '', strandNumber: null, subStrandName: '', subStrandNumber: null })],
      'mathematics'
    )
    expect(tree[0].name).toBe('Strand ?')
    expect(tree[0].subStrands[0].name).toBe('Sub-strand ?')
  })

  it('falls back to the indicator code when a standard has no code of its own', () => {
    const tree = buildTree([ind({ contentStandardCode: undefined, code: 'B4.9.9.9.9' })], 'mathematics')
    expect(tree[0].subStrands[0].standards[0].code).toBe('B4.9.9.9.9')
  })

  it('is empty for an unknown subject and survives an empty list', () => {
    expect(buildTree([ind()], 'computing')).toEqual([])
    expect(buildTree([], 'mathematics')).toEqual([])
  })
})
