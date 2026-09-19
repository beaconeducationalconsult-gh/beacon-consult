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

// creative-arts_B2_curriculum_db_clean.json -> creative_arts_b2_lessons_enriched.json
const lessonFileOf = (dbFile) => {
  const stem = dbFile.replace('_curriculum_db_clean.json', '').replace(/-/g, '_')
  const [subject, grade] = [stem.replace(/_(B\d|KG\d)$/i, ''), stem.match(/_(B\d|KG\d)$/i)?.[1]]
  return grade ? `${subject}_${grade.toLowerCase()}_lessons_enriched.json`
    : `${subject}_lessons_enriched.json`
}

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

    it('serves every subject-grade from the audited copy', () => {
      // Nine subject-grades used to be served from data/reference/, the fallback
      // copy: computing and french B4–B6, kindergarten KG1/KG2 and
      // english-language B5. `scripts/promote_reference_subjects.py` moved their
      // databases and summaries into data/curriculum/ (2026-09-18), so the
      // fallback is no longer what anyone reads — the drifted copies that remain
      // there (creative-arts B4–B6, social-studies B7–B9, english-language's own
      // older extracts) are inert, and this assertion is what keeps them that way.
      const fromReference = all.filter((s) => s.source !== 'curriculum').map(pair).sort()
      expect(fromReference).toEqual([])
    })

    it('audits the promoted subject-grades with a check that can be re-run', () => {
      // Audit A never used to see these nine: it enumerates data/curriculum/, and
      // their databases lived in the fallback copy. Two of them were pinned to
      // Audit B for that reason (english-language B5, TODO P1-9). Now both audits
      // cover all 84 subject-grades, so either row can be re-derived by anyone.
      const fromA = auditPasses('audit_a_results.json')
      const fromB = auditPasses('audit_b_results.json')
      for (const name of [
        'B4 computing', 'B5 computing', 'B6 computing',
        'B4 french', 'B5 french', 'B6 french',
        'KG1 kindergarten', 'KG2 kindergarten', 'B5 english-language',
      ]) {
        expect(fromA.has(name), `${name} in Audit A`).toBe(true)
        expect(fromB.has(name), `${name} in Audit B`).toBe(true)
      }
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
        const rows = readData(`curriculum/french_${grade}_curriculum_db_clean.json`)
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
        const rows = readData(`curriculum/french_${grade}_curriculum_db_clean.json`)
        for (const code of Object.keys(rows)) {
          if (!rows[code].cs_desc) empty.push(code)
        }
      }
      expect(empty).toEqual(['B6.1.2.5.3'])
    })

    it('serves those standards to the portal', () => {
      // The fill is only real if it survives the build — the three French B4-B6
      // subject-grades are served from data/curriculum/ since the promotion.
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
      // text glued in front of the statement — or in place of it. The served
      // copies were already clean; the repair was made to the *reference* copies,
      // which are what this test reads. One record is exempt: B7.4.2.3.1 is a stub
      // built from the front matter's worked example, which the print has no
      // content standard for (docs/TODO.md).
      const BLEED = /^(?:Communication and Collaboration|Critical Thinking and Problem Solving|Creativity and Innovation|Cultural identity and Global Citizenship|Personal development and leadership|Digital literacy|Core Competenc|French Content Standard)/i
      const exempt = new Set(['B7.4.2.3.1'])
      const bad = []
      for (const grade of ['B7', 'B8', 'B9']) {
        const rows = readData(`curriculum/french_${grade}_curriculum_db_clean.json`)
        for (const code of Object.keys(rows)) {
          if (!exempt.has(code) && BLEED.test(rows[code].cs_desc || '')) bad.push(`${code}: ${rows[code].cs_desc}`)
        }
      }
      expect(bad).toEqual([])
    })
  })

  describe('the reference-only text fields', () => {
    const readData = (path) => JSON.parse(readFileSync(new URL(`../data/${path}`, import.meta.url), 'utf8'))
    // the eight subject-grades no audited database covered, promoted into
    // data/curriculum/ by scripts/promote_reference_subjects.py
    const referenceOnly = [
      'computing_B4', 'computing_B5', 'computing_B6',
      'french_B4', 'french_B5', 'french_B6',
      'kindergarten_KG1', 'kindergarten_KG2',
    ]
    const servedFor = (name) => {
      const [subject, grade] = name.split('_')
      return bundle.get(grade).indicators.filter((i) => i.subjectId === subject)
    }

    it('gives every record of the eight reference-only subject-grades a keyword tag', () => {
      // No NaCCA print carries keywords, so there is nothing to read from one: the
      // audited subject-grades carry a single `subject, grade, band` tag per file,
      // and the extraction had left all 812 records of these eight empty (the six
      // drifted copies in data/reference/ are covered by the same pass).
      const empty = []
      for (const name of referenceOnly) {
        const rows = readData(`curriculum/${name}_curriculum_db_clean.json`)
        const codes = Object.keys(rows)
        expect(codes.length, `${name} records`).toBeGreaterThan(20)
        for (const code of codes) {
          if (!String(rows[code].keywords || '').trim()) empty.push(`${name}/${code}`)
        }
      }
      expect(empty).toEqual([])
    })

    it('serves those tags to the portal', () => {
      const empty = []
      for (const name of referenceOnly) {
        for (const i of servedFor(name)) if (!String(i.keywords || '').trim()) empty.push(i.id)
      }
      expect(empty).toEqual([])
    })

    it('serves no page furniture in their descriptions', () => {
      // The extraction read the page top to bottom, so the footer (`© NaCCA,
      // Ministry of Education 2019 44`), the column headings and the
      // core-competence labels of the column next door ended up inside indicator
      // descriptions — 94 records ended with the footer, 62 carried the
      // competence list, and the headings were in dozens more.
      // scripts/fix_reference_text.py deletes only what the print sets outside the
      // record's own row, and this is the check that it did, over the served copy.
      const FURNITURE = [
        /©\s*NaCCA/i,
        /Indicators? and Exemplars?/i,
        /Core Competenc/i,
        /Subject Specific Practice/i,
        /Communication and Collaboration/i,
        /Critical Thinking/i,
        /Creativity and Innovation/i,
        /Cultural Identity and Global Citizenship/i,
        /Personal Development and Leadership/i,
        /Digital Literacy/i,
      ]
      const hits = []
      for (const name of referenceOnly) {
        for (const i of servedFor(name)) {
          const text = String(i.description || '')
          const seen = FURNITURE.filter((rx) => rx.test(text))
          if (seen.length) hits.push(`${i.id}: ${seen[0]}`)
        }
      }
      expect(hits).toEqual([])
    })

    it('gives the kindergarten content standards the sentence the print prints', () => {
      // The KG print sets the standard in its own column. Thirteen records held
      // nothing, seven stopped short of the sentence, twenty-one carried the
      // sentence plus the heading of the column next door, and five (K2.5.1.1)
      // held indicator-column text instead — all of them are settled against the
      // print. K1.3.2.1's own cell is blank in the print, so its five records stay
      // empty rather than being guessed at.
      const empty = []
      for (const grade of ['KG1', 'KG2']) {
        const rows = readData(`curriculum/kindergarten_${grade}_curriculum_db_clean.json`)
        for (const code of Object.keys(rows)) {
          if (!String(rows[code].cs_desc || '').trim()) empty.push(code)
        }
      }
      expect(empty.sort()).toEqual([
        'K1.3.2.1.1', 'K1.3.2.1.2', 'K1.3.2.1.3', 'K1.3.2.1.4', 'K1.3.2.1.5',
      ])

      // the two standards whose column the print was read for at last
      const washed = []
      for (const [grade, prefix] of [['KG1', 'K1.3.1.1.'], ['KG2', 'K2.1.3.1.']]) {
        const rows = readData(`curriculum/kindergarten_${grade}_curriculum_db_clean.json`)
        for (const code of Object.keys(rows)) {
          if (code.startsWith(prefix) && !/^Demonstrate/.test(rows[code].cs_desc || '')) washed.push(code)
        }
      }
      expect(washed).toEqual([])

      // and the five records that held indicator text now hold the print's own
      // sentence for their standard
      const kg2 = readData('curriculum/kindergarten_KG2_curriculum_db_clean.json')
      for (const code of ['K2.5.1.1.3', 'K2.5.1.1.4', 'K2.5.1.1.5', 'K2.5.1.1.6', 'K2.5.1.1.7']) {
        expect(kg2[code].cs_desc, code).toBe('Demonstrate understanding of history and celebrations of Ghana')
      }
    })

    it('leaves a trail of what it wrote, and writes nothing it could not back', () => {
      const trail = readData('audit/reference_text_fixes.json')
      // The trail accumulates: the run that did the work is in `history`, and the
      // per-record evidence stays there after a later run finds nothing to do.
      expect(trail.history).toContainEqual({
        keywords: 812, keywords_drift: 182, ind_desc: 397, cs_desc: 176,
      })
      expect(trail.keywords.flatMap((k) => k.records)).toHaveLength(812)
      expect(Object.values(trail.ind_desc).reduce((n, e) => n + e.written, 0)).toBe(397)
      // …and the one content standard a later run filled is there too: computing's
      // B5.6.4.9.1 was empty although the print prints the sentence (found when the
      // promotion put the file under Audit A's nose)
      expect(trail.history).toContainEqual({
        keywords: 0, keywords_drift: 0, ind_desc: 0, cs_desc: 1,
      })
      const computing = trail.cs_desc.find((e) => e.cs_code === 'B5.6.4.9')
      expect(computing.changes.map((c) => c.after))
        .toEqual(['Demonstrate proficiency in Digital Literacy.'])

      // every description it wrote is read back against the print, and the
      // strength of that reading is recorded per record; a survivor the print does
      // not carry is never written (`unverified`), so none may appear here
      const allowed = new Set([
        'row', 'page', 'row-order', 'page-order', 'document', 'document-order',
      ])
      const bad = []
      for (const [key, entry] of Object.entries(trail.ind_desc)) {
        for (const c of entry.changes) if (!allowed.has(c.where)) bad.push(`${key}/${c.code}: ${c.where}`)
      }
      expect(bad).toEqual([])
      expect(Object.values(trail.ind_desc).flatMap((e) => e.unverified)).toEqual([])

      // the five values displaced from K2.5.1.1 are kept here, not thrown away
      const displaced = trail.cs_desc
        .flatMap((e) => e.changes)
        .filter((c) => c.action === 'displaced')
        .map((c) => c.code)
        .sort()
      expect(displaced).toEqual([
        'K2.5.1.1.3', 'K2.5.1.1.4', 'K2.5.1.1.5', 'K2.5.1.1.6', 'K2.5.1.1.7',
      ])
    })

    it('took the print\u2019s exemplar tail back off the indicators it cut', () => {
      const trail = readData('audit/ind_desc_exemplars.json')
      // 242 stops and 11 the corrected column band exposed (the career-technology
      // print's content-standard edge sits at x≈59, which the reader had dropped)
      expect(trail.applied.records).toBe(253)
      expect(trail.applied.repeats + trail.applied.dangling).toBe(253)
      expect(trail.history[0]).toMatchObject({ records: 242, lesson_slots: 980 })
      expect(trail.history.at(-1)).toMatchObject({ records: 11, furniture_records: 27 })

      // a cut is only ever a deletion: what each record says now is a prefix of
      // what it said, and the print backed the reading before it was made
      for (const e of trail.cut) {
        expect(e.after.length, e.code).toBeLessThanOrEqual(e.before.length)
        expect(e.before.startsWith(e.after), e.code).toBe(true)
        // only the readings the print backs are written, and the strength of that
        // reading is recorded next to each one
        if (e.verified) expect(e.ratio, e.code).toBeGreaterThanOrEqual(0.9)
        else expect(e.reason, e.code).toBeTruthy()
      }

      // and the lesson template, which is a copy of the database, was cleaned with
      // it — the generated books read the lesson file, not the database
      expect(trail.applied.lesson_slots).toBe(1137)
      expect(trail.applied.lesson_fields).toMatchObject({
        ind_desc: 1137, perf_indicator: 1137, starter: 962, main: 962,
      })
      const slots = readData('lessons/creative_arts_b2_lessons_enriched.json')
      const dangling = slots.filter((s) => /learners? (are|is) to:?\s*$/i.test(s.ind_desc || ''))
      expect(dangling).toEqual([])
      const noTail = slots.filter((s) => s.ind_code === 'B2.1.1.1.1')
      expect(noTail.length).toBeGreaterThan(0)
      for (const slot of noTail) {
        expect(slot.ind_desc.endsWith('communities')).toBe(true)
        expect(slot.perf_indicator.endsWith('communities')).toBe(true)
        // the activity steps the template writes around the indicator are copies
        // too, and they are what the printed book actually shows
        for (const step of [...slot.starter, ...slot.main]) {
          expect(step, step).not.toMatch(/learners? (are|is) to:?$|1\. Identify drawing materials/)
        }
      }

      // the strongest form of the same claim, over every record the trail names:
      // no lesson field anywhere still carries a text the cleanup removed
      const before = new Map(trail.cut.filter((e) => e.verified)
        .map((e) => [`lessons/${lessonFileOf(e.file)}`, e.before]))
      const offenders = []
      for (const file of new Set(before.keys())) {
        for (const slot of readData(file)) {
          const b = before.get(file)
          if (b === undefined) continue
          if (slot.ind_desc === b) offenders.push(`${file}/${slot.lesson_num}/ind_desc`)
          // the other fields embed the indicator inside a sentence the template
          // writes around it, so the check is containment, not equality
          for (const field of ['perf_indicator', 'rpk']) {
            if ((slot[field] || '').includes(b)) offenders.push(`${file}/${slot.lesson_num}/${field}`)
          }
          for (const field of ['starter', 'main', 'plenary']) {
            for (const step of slot[field] || []) {
              if (step.includes(b)) offenders.push(`${file}/${slot.lesson_num}/${field}`)
            }
          }
        }
      }
      expect(offenders).toEqual([])

      // the record the artefact names first is the one the audit trail describes
      const first = trail.cut.find((e) => e.verified)
      const rows = readData(`curriculum/${first.file}`)
      expect(rows[first.code].ind_desc).toBe(first.after)

      // …and the neighbouring column, which some extractions copied into the same
      // field: every removed span is text the print sets beside the indicator, and
      // what is left is either the print's own row or an indicator restored from it
      expect(trail.furniture.filter((e) => e.verified)).toHaveLength(27)
      for (const e of trail.furniture) {
        if (!e.verified) continue
        expect(e.removed.length, e.code).toBeGreaterThan(0)
        for (const span of e.removed) expect(e.before.includes(span), `${e.code}: ${span}`).toBe(true)
        expect(e.after.length).toBeLessThan(e.before.length)
        expect(e.proof.every((p) => p.in_side_column), e.code).toBe(true)
      }
      const restored = trail.furniture.filter((e) => e.restored_from_print)
      expect(restored.map((e) => e.code).sort()).toEqual(['B9.1.2.1.1', 'B9.2.4.1.1'])
      const computingB9 = readData('curriculum/computing_B9_curriculum_db_clean.json')
      expect(computingB9['B9.1.2.1.1'].ind_desc)
        .toBe('Evaluate problems in the community that can be solved with technology')
      expect(computingB9['B9.2.4.1.1'].ind_desc)
        .toBe('Perform data filtering, sorting and validation')
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
