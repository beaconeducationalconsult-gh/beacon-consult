.PHONY: install inventory audit audit-l2 check check-scripts bundle-size bundle-check books-rollout books-generate books-publish deploy-storage questions build-questions generate-questions bundle-hash verify-deploy deploy-check preflight dev build lint test test-rules preview deploy-rules books book-skeleton build-curriculum validate-curriculum generate-schemes generate-records package-books

# ── Frontend (React + Vite + Yarn 4) ────────────────────────────────────────
# The portal lives at the repository root. Node 22+ and Yarn 4 are required:
#   corepack enable && corepack prepare yarn@4.9.4 --activate
# Override the binary when yarn is not on PATH, e.g.
#   make check YARN=/path/to/yarn
YARN ?= yarn

install:
	$(YARN) install

dev:
	$(YARN) dev

build:
	$(YARN) build

preview:
	$(YARN) preview

lint:
	$(YARN) lint

# Unit tests + contract tests over the committed curriculum bundle (vitest).
test:
	$(YARN) test

# The rules suite against the Firestore emulator (tests/rules/). Kept out of
# `check` because the emulator is a JVM program: a machine without Java 21
# cannot run it, and `make check` must not depend on one being installed. It
# also downloads firebase-tools and the emulator jar on its first run, so it
# needs the network. CI runs it in its own job, where both are guaranteed.
test-rules:
	$(YARN) test:rules

# ── Everything that must pass before a deploy ───────────────────────────────
# The build is included so that "yarn build fails" cannot be discovered for the
# first time in production, and the audit is included because an inventory
# *error* means the portal would serve part of the dataset it cannot source.
# The tests include contract checks over public/curriculum itself, so a bundle
# that does not join up fails here rather than in a teacher's browser.
check: questions lint test check-scripts validate-curriculum inventory bundle-size bundle-check bundle-hash
	$(YARN) build

# Cheap guard for the P2-3 contract: the build writes a bundleHash and the service
# worker reads it. Full deploy verification is `make deploy-check URL=…`.
bundle-hash:
	python3 scripts/verify_deploy.py --offline-check

# ── Firebase (rules + indexes) ──────────────────────────────────────────────
# .firebaserc pins the project, so no --project flag is needed.
# Override with: make deploy-rules FIREBASE=/path/to/firebase
#
# Run `make check` first — this pushes the rules that enforce everything the
# app does, and a bad publish locks every member out of production.
FIREBASE ?= firebase

deploy-rules:
	$(FIREBASE) deploy --only firestore:rules,firestore:indexes

# Storage rules are a separate deploy too (P3-3): they gate the generated-document
# library. `firebase deploy --only storage` uses the "storage" block in firebase.json.
deploy-storage:
	$(FIREBASE) deploy --only storage

# ── Dataset audit ───────────────────────────────────────────────────────────
# `make inventory` derives every headline number from data/ and separates:
#   errors   -> the portal cannot serve part of the dataset (release blocker)
#   legacy   -> the retired NCOS app's module manifest (reference only; the
#               portal has no modules, so this never fails the audit)
#   warnings -> known, honest data gaps (e.g. the 8 bundle pairs backed only by
#               data/reference/)
# Run it before any data change and after `make build-curriculum`.
audit: inventory

# What in L2 is per-lesson content and what is a subject-wide template (P1-4).
# Writes data/audit/l2_template.json; changes no data. `make check` fails if the
# app's own list of routine fields drifts from this measurement.
audit-l2:
	python3 scripts/audit/audit_d_l2_template.py

# ── Python environment (data pipeline + book generation) ────────────────────
install-python:
	pip install -r requirements.txt

# ── Dataset inventory + agreement checks ────────────────────────────────────
# Derives every headline number in README.md / docs/curriculum-data.md from the
# data itself, and fails if the portal cannot serve part of the dataset.
# Read-only: never writes to data/ except data/inventory.json.
# Run `make audit` (or this target directly) when you want the full picture.
inventory:
	PYTHONPATH=. python scripts/build_inventory.py

# ── Kernel / module health (retired NCOS app — reference only) ──────────────
# The old `boot-check` / `list-modules` targets died with the 2026-09-17 fold-out:
# they called `tools/ncosctl.py`, which moved to `legacy/tools/` with the app it
# drives (and nothing in the portal imports it — see docs/TODO.md's retirement
# note). `make audit`'s LEGACY block is the kernel-vs-dataset reference now.

# ── Curriculum bundle (public/curriculum/) ──────────────────────────────────
# Builds the per-grade static JSON bundle the portal reads offline.
# Run this after any change to data/curriculum/ or data/lessons/.
build-curriculum:
	PYTHONPATH=. python scripts/build_app_curriculum.py

# What the committed bundle costs, and a budget it must not quietly pass (P2-6).
# The bundle is committed on purpose — see docs/curriculum-data.md.
bundle-size:
	python3 scripts/bundle_size_report.py

# The bundle is a committed build output, so it must match the data it is built
# from: rebuilding has to leave the tree unchanged. A stale bundle means the app
# serves data that no longer matches `data/curriculum/` or `data/lessons/`.
bundle-check:
	python3 scripts/build_app_curriculum.py > /dev/null
	@git diff --quiet -- public/curriculum || { \
		echo "public/curriculum/ does not match the data it is built from:"; \
		git diff --stat -- public/curriculum | tail -3; \
		echo "run 'make build-curriculum' and commit the result"; exit 1; }

# The question bank (P1-5): validate data/questions/ and copy it into the bundle.
# Report-only by default; `make build-questions` writes. See docs/curriculum-data.md.
questions:
	python3 scripts/build_question_bank.py
	python3 scripts/generate_question_bank.py --verify

build-questions:
	python3 scripts/build_question_bank.py --apply

generate-questions:
	python3 scripts/generate_question_bank.py

# The one-shot scripts under scripts/ are documentation as much as tools: a script
# that cannot import its own compatibility shim documents nothing (P2-8).
check-scripts:
	python3 scripts/check_scripts.py

# The offline half of scripts/verify_deploy.py: the local bundle hash exists and
# public/sw.js still names its cache after it. The full check needs a URL.
verify-deploy:
	python3 scripts/verify_deploy.py $(URL)

deploy-check: verify-deploy

# The same pre-flight for a machine with Node but no Python (Windows), plus the
# two checks only it makes: .env.local is complete, and a build actually carries
# the config. Both scripts are held to the same check list by
# src/deployCheck.test.js.
preflight:
	node scripts/verify_deploy.mjs $(URL)

validate-curriculum:
	PYTHONPATH=. python scripts/validate_app_curriculum.py

# ── Document generation (local, outputs to dist/) ──────────────────────────
generate-schemes:
	PYTHONPATH=. python scripts/generate_schemes.py --per-term

generate-records:
	PYTHONPATH=. python scripts/generate_records_of_work.py --per-term

package-books:
	PYTHONPATH=. python scripts/package_books.py

# ── Book skeletons (books/<grade>/, generated, never overwritten) ───────────
#   make book-skeleton SUBJECT=mathematics GRADE=B1
# Writes books/B1/mathematics-{textbook,workbook}-skeleton.docx; re-runs create
# -v2, -v3 … so an author's edited copy is never clobbered.
SUBJECT ?= mathematics
GRADE ?= B1
book-skeleton:
	python3 seed/build_book_skeleton.py $(SUBJECT) $(GRADE)

# The rollout (P3-1): report what exists and what is missing across the served
# subject-grades, build the missing ones, and keep data/books/manifest.json —
# `books/` is gitignored, so the manifest is what the repository knows about it.
# Needs python-docx (pip install -r requirements.txt).
books-rollout:
	python3 scripts/build_books_rollout.py

books-generate:
	python3 scripts/build_books_rollout.py --generate

books-publish:
	python3 scripts/build_books_rollout.py --subject $(SUBJECT) --grade $(GRADE) --publish
