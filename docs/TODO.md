# Project TODO

Live task list for the Beacon / staff-common-room work. Ordered by horizon:
**Now** is what unblocks revenue, **Next** is what compounds it, **Later** is
where the big bets live.

> Priority anchor, stated by the owner: **build the SaaS and generate revenue as
> soon as possible.** Anything that does not serve that goes in Later.

---

## Now — unblocks revenue

- [ ] **Take the current inventory to five schools and ask for the sale.**
      73 lesson plan books, 73 schemes, 365 records of work are all finished and
      unsold. This is the only item on this list that produces money rather than
      costing it. Everything else is in service of it.
- [ ] **Regenerate the gitignored output before any demo** (`dist/` and
      `app/public/curriculum/` are wiped from any fresh clone):
      ```bash
      python tools/build_app_curriculum.py
      python tools/generate_schemes.py --per-term
      python tools/generate_records_of_work.py --per-term
      python tools/package_books.py
      ```
- [ ] **Verify `yarn build` on a real machine** — the Materials screen has never
      been compiled (no npm registry in the dev sandbox).
- [ ] **Create a “How To” / Getting Started screen and reusable help component.**
      Start with student authentication: explain that teachers create pupils,
      issue the shared class code plus each pupil’s personal access code, and
      recover or reset credentials. Link the guidance from Student login,
      Classrooms, and the portal navigation; support printable login cards.
- [ ] **Write `storage.rules`** — still absent. Required the moment the portal
      writes generated files into a school's workspace.

## Next — compounds what's built

- [x] **Generation history in the school workspace** — done 2026-09-13.
      `generated_materials` collection, recorded on download, listed in the
      workspace and on the Generate screen. See `docs/SCHOOL_WORKSPACE.md`.
- [x] **Bind cover branding to the caller's school** — done 2026-09-13. Members
      of a school get its name pre-filled and the field disabled, so a document
      cannot be printed under another school's name.
- [ ] **Store generated documents, not just their metadata.** History is
      metadata only — there is no re-download. Persisting the `.docx` needs
      Cloud Storage, which needs `storage.rules`.
- [ ] **Chunk the 38 MB curriculum bundle** into per-grade-subject files
      (~50 KB). Blocks usable mobile performance and matters for offline packs.
- [ ] **Enable `REQUIRE_AUTH=1`** on the deployed Material Service. Currently
      off, which means anyone finding the URL can generate unlimited documents.
- [ ] **Fill the question bank** — zero questions exist. Highest-value content
      the project lacks. VCTM §18 gives the assessment architecture.

## Later — the big bets

- [ ] **Visualization engine** — an interactive learning-model library mapped to
      curriculum indicators. Largest idea on the list; see
      `docs/VISUALIZATION_ENGINE.md`. Start with a 3–5 model pilot, not 50.
- [ ] **VCTM pilot** — run the full Visual-Conceptual chain end to end on one
      subject-grade (suggested: Basic 6 Science or Basic 9 Mathematics) before
      scaling to all 4,040 indicators.
- [ ] **Offline packs** — downloadable subject/class bundles so schools without
      reliable connectivity can use the library. Prerequisite for the
      visualization engine being realistic in Ghanaian schools.
- [ ] **Decide whether `dist/` belongs in git** — currently gitignored, so it
      must be regenerated on every machine.

---

## Deferred by decision

Items considered and deliberately not being done:

| Item | Why not |
|---|---|
| Building the Studio as a separate web app | One author (the owner) — `tools/` + git already is the Studio. Revisit when a second content author joins. |
| Selling printed books as the primary channel | The owner intends to replace the consortium print model with a self-serve portal, not replicate it. |
| Porting the Python generators to JavaScript | They work and are tested; the Cloud Run wrapper reuses them as-is. |
