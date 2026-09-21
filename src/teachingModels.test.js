import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { MODEL_COMPONENTS } from './components/models'
import {
  PILOT, TEACHING_MODELS, attachIndicators, modelledSubjectGrades, modelsFor,
} from './lib/teachingModels'

/*
 * The teaching models (P3-4) are only teaching material if they teach something
 * that is *served*. These tests hold the catalogue to the bundle: every model
 * names indicators that exist for its own subject and grade, every component it
 * points at exists, and the pilot stays small — three to five models, not fifty.
 */

const root = new URL('../', import.meta.url)
const indicatorRows = (grade) =>
  JSON.parse(readFileSync(new URL(`public/curriculum/${grade.toLowerCase()}_indicators.json`, root), 'utf8'))

describe('the catalogue', () => {
  it('stays a pilot: three to five models', () => {
    expect(TEACHING_MODELS.length).toBeGreaterThanOrEqual(3)
    expect(TEACHING_MODELS.length).toBeLessThanOrEqual(5)
  })

  it('gives every model a unique id, a title and a component that exists', () => {
    const ids = new Set()
    for (const model of TEACHING_MODELS) {
      expect(ids.has(model.id), `${model.id} is used twice`).toBe(false)
      ids.add(model.id)
      expect(model.title.length).toBeGreaterThan(3)
      expect(model.blurb.length).toBeGreaterThan(20)
      expect(Object.keys(MODEL_COMPONENTS), `${model.id} → ${model.component}`).toContain(model.component)
    }
  })

  it('names a served subject-grade', () => {
    const grades = JSON.parse(readFileSync(new URL('public/curriculum/grades.json', root), 'utf8'))
    const gradeIds = new Set(grades.map((g) => g.id))
    for (const model of TEACHING_MODELS) {
      expect(gradeIds.has(model.grade), `${model.id}: ${model.grade} is not a served grade`).toBe(true)
      const subjects = JSON.parse(readFileSync(
        new URL(`public/curriculum/${model.grade.toLowerCase()}_subjects.json`, root), 'utf8'))
      expect(subjects.map((s) => s.id), `${model.id}: ${model.subjectId}`).toContain(model.subjectId)
    }
  })

  it('teaches indicators that are really served, one to four per model', () => {
    for (const model of TEACHING_MODELS) {
      expect(model.indicatorCodes.length).toBeGreaterThanOrEqual(1)
      expect(model.indicatorCodes.length).toBeLessThanOrEqual(4)
      const codes = new Set(indicatorRows(model.grade)
        .filter((row) => row.subjectId === model.subjectId)
        .map((row) => row.code))
      for (const code of model.indicatorCodes) {
        expect(codes.has(code), `${model.id} names ${code}, which ${model.subjectId} ${model.grade} does not serve`)
          .toBe(true)
      }
    }
  })

  it('covers the pilot with every model it lists', () => {
    const pilot = modelsFor(PILOT.subjectId, PILOT.grade)
    expect(pilot).toHaveLength(TEACHING_MODELS.length)
    expect(modelledSubjectGrades()).toEqual([{ subjectId: PILOT.subjectId, grade: PILOT.grade }])
  })
})

describe('attaching the curriculum', () => {
  const model = TEACHING_MODELS[0]
  const indicators = indicatorRows(model.grade)

  it('carries each indicator’s own wording, not a paraphrase', () => {
    const [first] = attachIndicators(model, indicators).indicators
    const served = indicators.find((row) => row.code === model.indicatorCodes[0])
    expect(first.description).toBe(served.description)
    expect(first.served).toBe(true)
  })

  it('marks an indicator the bundle no longer holds instead of hiding it', () => {
    const stranded = attachIndicators({ ...model, indicatorCodes: ['B9.9.9.9.9'] }, indicators).indicators
    expect(stranded[0].served).toBe(false)
    expect(stranded[0].description).toBe('')
  })
})

describe('the models are real screens', () => {
  const dir = new URL('src/components/models/', root)
  const files = readdirSync(dir).filter((name) => name.endsWith('.jsx'))

  it('has a file for every component in the registry', () => {
    for (const [key, Component] of Object.entries(MODEL_COMPONENTS)) {
      expect(typeof Component, key).toBe('function')
    }
    expect(files.length).toBe(Object.keys(MODEL_COMPONENTS).length)
  })

  it('makes each model interactive — state, not a picture', () => {
    for (const name of files) {
      const text = readFileSync(new URL(name, dir), 'utf8')
      expect(text, `${name} has no state`).toMatch(/useState/)
      expect(text, `${name} renders no control`).toMatch(/<input|<select|<button/)
    }
  })

  it('is reachable from the side panel', () => {
    const sidebar = readFileSync(new URL('src/components/Sidebar.jsx', root), 'utf8')
    expect(sidebar).toContain("/portal/models")
  })
})
