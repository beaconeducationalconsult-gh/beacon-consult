# Beacon — Opportunity Map

*What we own, what it's worth, and the order to attack it in.*
Companion to `REPO_ANALYSIS_REPORT.md`. Prepared 2026-09-11.

---

## 1. The asset — an honest inventory

| Asset | Volume | State |
|---|---|---|
| Curriculum database | **3,095 indicators**, B1–B9, 13 subjects, coded `B{grade}.{strand}.{substrand}.{standard}.{indicator}` | Complete, audited against source PDFs |
| Written lesson plans | **13,140** (73 grade-subjects × 180 lessons) | Complete, machine-generated from template |
| Published books | **73 DOCX** (one per grade-subject) | Complete — B1 v1/v2 conflict resolved, grade bands corrected |
| Source provenance | 24 official NaCCA PDFs + full cross-check audit trail | Strong — this is defensible |
| Web application | React/Firebase PWA, 17 collections, ~15 modules | Built, deployed, unfinished in places |
| Student quiz PWA | Offline-first Dexie app, B7–B9 | Partially built (has a 4-phase roadmap) |
| **Question bank** | **Zero questions** | ❌ Designed as user-generated; empty |

### The one thing nobody else has

Not the lesson plans — plenty of people sell lesson plan booklets. It's this:

> **A machine-readable, indicator-level map of Ghana's entire basic curriculum, with
> term/week scheduling, that lets you compute what has and hasn't been taught.**

Every product below either is that, or gets stronger because of it.

---

## 2. Market (grounded, not guessed)

| Fact | Number | Source |
|---|---|---|
| Teachers in public primary schools | ~**94,000** | MoE 2025 PBB |
| Primary schools (public + private) | **25,359** (15,717 + 9,642) | MoE 2025 PBB |
| Learners, basic education | ~**6.15 million** | MoE 2025 PBB |
| BECE candidates per year | **619,985** (2026), from 20,390 schools | WAEC / Graphic |
| BECE candidates scoring grade 9 in Maths or English | **35,382** (2026) | MoE via yen.com.gh |
| Practising teachers lacking professional qualifications | **42,000+** | NTC / GES Updates |
| Accredited CPD providers | 13 accredited + 50 renewed (2024) | MoE 2025 PBB |

**What this tells us:** the volume is in teachers (94k+), the *money* is in schools
(25k institutions with budgets), the *urgency* is in B7–B9 (620k exam candidates), and
the *institutional channel* is CPD accreditation (a government-recognised route to
budgeted spend rather than out-of-pocket teacher spend).

---

## 3. Four product tiers

### Tier 1 — Inventory you can sell this month

| Product | Effort | Why it wins |
|---|---|---|
| **The 73 lesson plan books** | None — already built | Zero marginal cost. Cash now. |
| **Schemes of Learning** (73 × 3 terms) | Low — generator already exists in the app | **The recurring product.** Every teacher must submit one every term. The compliance artifact. Creates a reason to return 3× a year. |
| **Records of Work / weekly forecasts** | Low | The thing headteachers actually collect and sign. |

> ⚠️ **The single biggest gap in this repo is that there is not one Scheme of Learning
> document in it.** You own the generator and the data and never shipped the output.

### Tier 2 — Finish the product you already built (1–3 months)

| Product | What's blocking | Payoff |
|---|---|---|
| **School licensing** | Nothing — `schools`, `school_codes`, `school_admin` are built | 25,359 schools. Annual contracts beat individual subs. |
| **Student quiz PWA** | Finish the 4-phase roadmap in the zip | 620k BECE candidates/yr. Offline-first is correct for Ghana. |
| **BECE mock papers** | Need to *generate* questions (bank is empty) | Highest-value content you don't have. |

### Tier 3 — The moat (differentiated, hard to copy)

| Product | Why only you can |
|---|---|
| **Curriculum coverage analytics** for schools/chains/districts | Requires the indicator map + scheduling. `SchoolCoverage.jsx` already started. |
| **Textbook / publisher alignment** | You own the reference key publishers must map to. |
| **CPD content + NTC accreditation** | 13,140 lessons are ready-made training material; accreditation unlocks institutional budgets. |
| **Remediation keyed to failure data** | 35,382 kids failed on *specific* indicators; your whole model is indicator-keyed. |
| **Vernacular lesson plans** (Twi, Ewe, Ga, Dagbani, Hausa) | Your Ghanaian Language data is English-medium. Real vernacular content is scarce. |
| **Licensing the dataset / API** | Structured NaCCA-aligned curriculum is rare in any form. |

---

## 4. Pricing framework (GHS)

> ⚠️ **These are anchors, not facts.** Validate with five pilot schools before printing
> anything. Ghanaian private school budgets vary by an order of magnitude.

### Teachers (individual, digital delivery)

| SKU | Contents | Price |
|---|---|---|
| Single volume | 1 subject-grade, 180 lessons | **GHS 60** |
| Class teacher set | All subjects for one grade (7–10 volumes) | **GHS 300** |
| Subject specialist set | One subject across B1–B9 (9 volumes) | **GHS 400** |
| Printed & bound volume | Per volume, print-on-demand | **GHS 150–250** |

### Schools (annual licence) — the real business

| Plan | Contents | Price / yr |
|---|---|---|
| **Starter** | 1 campus · 10 teacher seats · full lesson plan library + schemes | **GHS 2,000** |
| **Standard** | 1 campus · unlimited seats · + coverage dashboard + question bank | **GHS 4,500** |
| **Chain** | 3+ campuses · central reporting · onboarding & training | **from GHS 12,000** |

**Petite maths:** Standard at GHS 4,500 × 100 schools = **GHS 450,000/yr**.
That's 100 of 25,359 schools — 0.4% penetration.

---

## 5. Go-to-market that actually works in Ghana

1. **Lead with the proprietor, not the teacher.** Teachers don't have budgets;
   proprietors do, and they care about *standardisation* and *inspection readiness* —
   exactly what the coverage dashboard sells.
2. **Sell the scheme, keep them with the plan.** Schemes of Learning are the mandatory,
   recurring, painful artifact. Use them as the wedge; the lesson plan library is what
   makes the renewal obvious.
3. **WhatsApp is the channel.** MoMo for payment, WhatsApp for delivery and support.
   Don't build a funnel that requires a credit card.
4. **Pilot five schools, free, for one term** — in exchange for a logo, a testimonial, and
   coverage data you can show the next fifty.
5. **CPD accreditation as the institutional channel.** NTC-accredited CPD lets schools
   spend budgeted training money on you instead of out-of-pocket.
6. **Fix billing last, not first.** Manual MoMo confirmation (what you have) is fine
   until ~50 paying schools. Automate when the admin loop actually hurts.

---

## 6. The 90-day plan (revenue now, SaaS in parallel)

**Weeks 1–2 — unlock cash**
- Resolve the B1 v1/v2 conflict; pick a canonical set.
- Publish the catalogue; open MoMo + WhatsApp ordering.
- Sell to 10 teachers and 2 schools manually. Learn the objections.

**Weeks 3–6 — build the recurring product**
- Generate all **219 Schemes of Learning** (73 × 3 terms) from existing data.
- Ship the **school one-pager** + **marketing video** (see `marketing/`).
- Unzip the app into a runnable repo; fix the broken `/home/user/curriculum_db` paths.

**Weeks 7–10 — make the school product real**
- Generate `public/curriculum/*.json` for **B2–B9** (currently only B1 is scripted).
- Finish the **coverage dashboard** — this is the demo that closes proprietors.
- Run 5 free school pilots.

**Weeks 11–13 — institutional**
- Start NTC CPD accreditation.
- Publish first BECE mock papers for B7–B9.
- Convert pilots to paid; open the school licence properly.

---

## 7. Risks — read before selling anything

| Risk | Severity | Mitigation |
|---|---|---|
| **Generated pedagogy is templated.** "ACTIVITY 1 (Concrete – 5 min): Teacher models with manipulatives…" is sound scaffolding, not inspired teaching. | 🔴 High | Human editorial pass on at least one flagship set before approaching premium schools. Never claim "written by expert teachers." |
| **B1 has two competing versions** (v1 vs v2) with different session structures. | 🟠 Medium | Decide this week; archive the loser. |
| **Coverage gaps:** no OWOP for B2–B6; no KG in the root dataset. | 🟠 Medium | Disclose, or fill before selling "complete" bundles. |
| **Question bank is empty** — any assessment product needs real generation work. | 🟠 Medium | Don't promise BECE papers until questions exist. |
| **App can't run from the repo** (sealed in a ZIP, broken paths, no `package.json` at root). | 🟠 Medium | Week-3 task above. |
| **Firestore rules are committed but not necessarily deployed.** | 🟠 Medium | `firebase deploy --only firestore:rules,firestore:indexes` in every release. |
| **NaCCA may revise the curriculum.** Your B7–B9 sources are *draft* CCP documents. | 🟡 Low | Version everything; keep the PDF-to-JSON pipeline runnable so you can re-extract. |
| **Data provenance ≠ licence to sell.** The curriculum is public; your *expression* of it is yours. | 🟡 Low | Sell the authored lesson text and the tooling, not the standards themselves. |

---

## 8. Bottom line

You have finished inventory, a proven pipeline, and a rare dataset — but no product
packaged for a buyer and no recurring artifact. The two moves that matter most are:

1. **Ship Schemes of Learning.** It's the only thing you can build in weeks that schools
   are *obligated* to buy three times a year.
2. **Sell to proprietors on coverage, not to teachers on convenience.** The dashboard is
   the demo; the lesson plans are the evidence.

Everything else — quizzes, BECE, CPD, vernacular, data licensing — compounds off those two.
