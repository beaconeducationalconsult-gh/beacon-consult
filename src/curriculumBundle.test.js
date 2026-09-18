import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { buildTree } from './hooks/useCurriculum'

/**
 * Contract tests over the *real* committed bundle in public/curriculum.
 *
 * The portal once rendered an empty curriculum browser because a grade id was
 * looked up as a subject id — the data was fine, nothing checked the join. These
 * assertions encode the relationships the UI assumes, so a broken or rebuilt
 * bundle fails here rather than in front of a teacher.
 */
const read = (name) => JSON.parse(readFileSync(new URL(`../public/curriculum/${name}`, import.meta.url), 'utf8'))

const grades = read('grades.json')
const ids = grades.map((g) => g.id)
const bundle = new Map(
  ids.map((id) => {
    const key = id.toLowerCase()
    return [id, { subjects: read(`${key}_subjects.json`), indicators: read(`${key}_indicators.json`) }]
  })
)

const flatten = (tree) =>
  tree.flatMap((s) => s.subStrands.flatMap((sub) => sub.standards.flatMap((std) => std.indicators)))

describe('the grade list', () => {
  it('covers KG1 to B9', () => {
    expect(ids).toEqual(['KG1', 'KG2', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9'])
  })

  it('has a subjects and an indicators file for every grade', () => {
    for (const [grade, { subjects, indicators }] of bundle) {
      expect(Array.isArray(subjects), `${grade} subjects`).toBe(true)
      expect(Array.isArray(indicators), `${grade} indicators`).toBe(true)
      expect(subjects.length, `${grade} has subjects`).toBeGreaterThan(0)
      expect(indicators.length, `${grade} has indicators`).toBeGreaterThan(0)
    }
  })
})

describe.each(ids)('%s', (grade) => {
  const { subjects, indicators } = bundle.get(grade)
  const subjectIds = subjects.map((s) => s.id)
  const indicatorSubjects = new Set(indicators.map((i) => i.subjectId))

  it('gives every subject an id and a name', () => {
    for (const subject of subjects) {
      expect(subject.id, `${grade} subject id`).toBeTruthy()
      expect(subject.name, `${grade}/${subject.id} name`).toBeTruthy()
    }
  })

  // The join the whole browser hangs off: subject ids in the subjects file must
  // be the subjectId stamped on indicators. An orphan means a subject that can
  // never show any indicators.
  it('joins subjects to indicators in both directions', () => {
    const orphans = [...indicatorSubjects].filter((id) => !subjectIds.includes(id))
    expect(orphans, `${grade} indicators with no matching subject`).toEqual([])

    const empty = subjectIds.filter((id) => !indicatorSubjects.has(id))
    expect(empty, `${grade} subjects with no indicators`).toEqual([])
  })

  it('stamps the grade on every indicator', () => {
    const wrong = indicators.filter((i) => i.grade !== grade)
    expect(wrong.length, `${grade} indicators stamped with another grade`).toBe(0)
  })

  // `id` is namespaced (`mathematics_B4.1.1.1.1`) and is what
  // validate_app_curriculum.py checks. It is the key lesson plans store.
  it('keeps indicator ids unique within the grade', () => {
    const seen = new Set()
    const duplicates = new Set()
    for (const { id } of indicators) {
      if (seen.has(id)) duplicates.add(id)
      seen.add(id)
    }
    expect([...duplicates], `${grade} duplicate indicator ids`).toEqual([])
  })

  // `code` carries no subject namespace — `B4.1.1.1.1` exists in all ten B4
  // subjects — so uniqueness only holds per subject-grade. Anything keyed on a
  // bare code has to be scoped by subject (or use `id`).
  it('keeps indicator codes unique within a subject, not across the grade', () => {
    for (const subjectId of new Set(indicators.map((i) => i.subjectId))) {
      const codes = indicators.filter((i) => i.subjectId === subjectId).map((i) => i.code)
      const duplicates = codes.filter((code, index) => codes.indexOf(code) !== index)
      expect([...new Set(duplicates)], `${grade}/${subjectId} duplicate codes`).toEqual([])
    }
  })

  it('carries the numbers the UI sorts by', () => {
    for (const indicator of indicators) {
      expect(typeof indicator.strandNumber, `${grade}/${indicator.code} strandNumber`).toBe('number')
      expect(typeof indicator.subStrandNumber, `${grade}/${indicator.code} subStrandNumber`).toBe('number')
      expect(indicator.contentStandardCode || indicator.code, `${grade}/${indicator.code} standard`).toBeTruthy()
    }
  })

  it('builds a non-empty tree for every subject, losing nothing', () => {
    for (const subjectId of subjectIds) {
      const expected = indicators.filter((i) => i.subjectId === subjectId)
      const tree = buildTree(indicators, subjectId)

      expect(tree.length, `${grade}/${subjectId} strands`).toBeGreaterThan(0)
      expect(flatten(tree).length, `${grade}/${subjectId} indicators kept`).toBe(expected.length)

      // every indicator keeps its identity through the nesting
      const kept = flatten(tree).map((i) => i.id).sort()
      expect(kept).toEqual(expected.map((i) => i.id).sort())
    }
  })
})

  describe('provenance', () => {
    const all = [...bundle.values()].flatMap((b) => b.subjects)
    const pair = (s) => `${s.grade} ${s.id}`

    // Audit B works in indicator codes, and kindergarten prints K1./K2. where
    // the bundle labels that grade KG1/KG2 from the file name.
    const GRADE_ALIASES = { K1: 'KG1', K2: 'KG2' }
    const auditPasses = (file) => {
      const rows = JSON.parse(readFileSync(new URL(`../data/audit/${file}`, import.meta.url), 'utf8'))
      return new Set(
        rows
          .filter((r) => r.status === 'PASS')
          .map((r) => {
            const grade = String(r.grade).toUpperCase()
            return `${GRADE_ALIASES[grade] || grade} ${String(r.subject).toLowerCase()}`
          })
      )
    }

    it('names the official source for every served subject', () => {
      // Eight summaries shipped with an empty sourceUrl and no counts block:
      // computing and french B4–B6, and both kindergarten grades. Nobody could
      // tell where the data came from, which is why they could never be
      // audited. Every subject now names its source.
      const missing = all.filter((s) => !s.sourceUrl).map(pair)
      expect(missing).toEqual([])
    })

    it('states, on every subject, whether the source has been checked', () => {
      // `verified` is stamped by the build from the audit results, so it cannot
      // silently go missing — an absent field would read as "fine" in any
      // `s.verified === false` check in the UI.
      const unstated = all.filter((s) => typeof s.verified !== 'boolean')
      expect(unstated.map(pair)).toEqual([])
    })

    it('has now cross-checked every served subject against its source', () => {
      // This is where P1-1 landed. Eight subject-grades used to be served
      // un-cross-checked and were flagged as such in the UI; Audit B, which
      // re-extracts every code from the source PDF, now covers all of them.
      //
      // The flag stays a guard rather than becoming decoration: a new
      // subject-grade that has not been cross-checked fails here.
      const unverified = all.filter((s) => s.verified === false).map(pair)
      expect(unverified).toEqual([])
    })

    it('earns `verified` from an audit result, not from a default', () => {
      // The test above would also pass if the build stamped `verified: true`
      // unconditionally, so check the flag against the audit outputs it claims
      // to come from. Passing either audit counts: Audit A compares indicator
      // counts, Audit B re-extracts every code from the PDF.
      const passes = new Set([
        ...auditPasses('audit_a_results.json'),
        ...auditPasses('audit_b_results.json'),
      ])
      // Guard against a vacuous pass — unreadable or empty audits must not make
      // the assertion below trivially true.
      expect(passes.size).toBeGreaterThan(50)
      const unsupported = all.filter((s) => s.verified === true && !passes.has(pair(s)))
      expect(unsupported.map(pair)).toEqual([])
    })

    it('serves exactly nine subject-grades from the reference copy', () => {
      // These exist only in data/reference/, so the build's DB_SEARCH order
      // falls back to that copy. They passed Audit B, which resolves each
      // database through find_data and so sees both directories — that is why
      // they can be verified while still being served from the second copy.
      //
      // Named explicitly: the list changing is a data-layout decision worth
      // noticing (promoting one into data/curriculum/ should update this).
      const fromReference = all.filter((s) => s.source !== 'curriculum').map(pair).sort()
      expect(fromReference).toEqual([
        'B4 computing',
        'B4 french',
        'B5 computing',
        'B5 english-language',
        'B5 french',
        'B6 computing',
        'B6 french',
        'KG1 kindergarten',
        'KG2 kindergarten',
      ])
    })

    it('audits english-language B5 with a check that can be re-run', () => {
      // Audit A passed this one before the data restructure, and its database
      // now lives only in data/reference/, where Audit A cannot see it — so its
      // committed PASS row cannot be reproduced (TODO P1-9). Audit B has no
      // such blind spot, which is what keeps the subject verified rather than
      // resting on a result nobody can re-derive.
      expect(auditPasses('audit_b_results.json').has('B5 english-language')).toBe(true)
    })
  })


  describe('the French content standards', () => {
    const readData = (path) => JSON.parse(readFileSync(new URL(`../data/${path}`, import.meta.url), 'utf8'))

    // The French B4–B6 print does not carry sentence-style content standards:
    // its CONTENT STANDARDS column holds one of four skill areas, and the SCOPE
    // AND SEQUENCE table (pp. xviii–xx) lists exactly those four — in this
    // order — for every sub-strand. The front matter (p. xvii) makes the fourth
    // component of an indicator code the content-standard number, so the
    // standard a record belongs to is decided by its own code.
    const SKILLS = {
      1: 'Compréhension Orale',
      2: 'Production Orale',
      3: 'Compréhension Écrite',
      4: 'Production Écrite',
    }
    const skillOf = (csCode) => SKILLS[String(csCode).split('.')[3]] || ''

    it('names the content standard of every French B4-B6 record', () => {
      // The field was empty for 262 of 267 records before
      // scripts/fix_french_content_standards.py filled it.
      const wrong = []
      for (const grade of ['B4', 'B5', 'B6']) {
        const rows = readData(`reference/french_${grade}_curriculum_db_clean.json`)
        const codes = Object.keys(rows)
        expect(codes.length, `${grade} records`).toBeGreaterThan(50)
        for (const code of codes) {
          const expected = skillOf(rows[code].cs_code)
          if (rows[code].cs_desc !== expected) {
            wrong.push(`${code} (${rows[code].cs_code}) -> ${JSON.stringify(rows[code].cs_desc)}`)
          }
        }
      }
      expect(wrong).toEqual([])
    })

    it('leaves the one content standard the print mis-numbers empty', () => {
      // B6.1.2.5 is numbered as a fifth content standard in a sub-strand whose
      // scope table lists four, so there is no skill to name — the print's own
      // defect, and the only record this project leaves without a standard.
      const empty = []
      for (const grade of ['B4', 'B5', 'B6']) {
        const rows = readData(`reference/french_${grade}_curriculum_db_clean.json`)
        for (const code of Object.keys(rows)) {
          if (!rows[code].cs_desc) empty.push(code)
        }
      }
      expect(empty).toEqual(['B6.1.2.5.3'])
    })

    it('serves those standards to the portal', () => {
      // The fill is only real if it survives the build: the three French
      // B4-B6 subject-grades are served from data/reference/.
      const rows = ['B4', 'B5', 'B6'].flatMap((grade) =>
        bundle.get(grade).indicators.filter((i) => i.subjectId === 'french')
      )
      expect(rows.length).toBe(266 + 1)
      const wrong = rows
        .filter((i) => i.contentStandardDescription !== skillOf(i.contentStandardCode))
        .map((i) => `${i.code} -> ${JSON.stringify(i.contentStandardDescription)}`)
      expect(wrong).toEqual([])
      // …and the one print defect is served as empty rather than guessed at.
      expect(rows.filter((i) => !i.contentStandardDescription).map((i) => i.code)).toEqual(['B6.1.2.5.3'])
    })

    it('does not mistake the core-competence column for a content standard', () => {
      // In French B7-B9 the CORE COMPETENCIES column sits beside the CONTENT
      // STANDARD column, and eleven standards (37 records) had the neighbour's
      // text glued in front of the statement — or in place of it. One record is
      // exempt: B7.4.2.3.1 is a stub built from the front matter's worked
      // example, which the print has no content standard for (docs/TODO.md).
      const BLEED = /^(?:Communication and Collaboration|Critical Thinking and Problem Solving|Creativity and Innovation|Cultural identity and Global Citizenship|Personal development and leadership|Digital literacy|Core Competenc|French Content Standard)/i
      const exempt = new Set(['B7.4.2.3.1'])
      const bad = []
      for (const grade of ['B7', 'B8', 'B9']) {
        const rows = readData(`reference/french_${grade}_curriculum_db_clean.json`)
        for (const code of Object.keys(rows)) {
          if (!exempt.has(code) && BLEED.test(rows[code].cs_desc || '')) bad.push(`${code}: ${rows[code].cs_desc}`)
        }
      }
      expect(bad).toEqual([])
    })
  })

  describe('known gaps stay known', () => {
    it('has no schedules file for the kindergarten grades', () => {
    const kg = grades.filter((g) => g.id.startsWith('KG'))
    for (const grade of kg) expect(grade.hasSchedules).toEqual([])

    // and that is a deliberate gap, not a missing build: every other grade has one
    for (const grade of grades.filter((g) => !g.id.startsWith('KG'))) {
      expect(grade.hasSchedules.length, `${grade.id} schedules`).toBeGreaterThan(0)
    }
  })
})
