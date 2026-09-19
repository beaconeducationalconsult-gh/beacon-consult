.PHONY: install inventory audit check check-scripts dev build lint test preview deploy-rules books book-skeleton boot-check list-modules build-curriculum validate-curriculum generate-schemes generate-records package-books

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

# ── Everything that must pass before a deploy ───────────────────────────────
# The build is included so that "yarn build fails" cannot be discovered for the
# first time in production, and the audit is included because an inventory
# *error* means the portal would serve part of the dataset it cannot source.
# The tests include contract checks over public/curriculum itself, so a bundle
# that does not join up fails here rather than in a teacher's browser.
check: lint test check-scripts validate-curriculum inventory
	$(YARN) build

# ── Firebase (rules + indexes) ──────────────────────────────────────────────
# .firebaserc pins the project, so no --project flag is needed.
# Override with: make deploy-rules FIREBASE=/path/to/firebase
#
# Run `make check` first — this pushes the rules that enforce everything the
# app does, and a bad publish locks every member out of production.
FIREBASE ?= firebase

deploy-rules:
	$(FIREBASE) deploy --only firestore:rules,firestore:indexes

# ── Dataset audit ───────────────────────────────────────────────────────────
# `make inventory` derives every headline number from data/ and separates:
#   errors   -> the portal cannot serve part of the dataset (release blocker)
#   legacy   -> the retired NCOS app's module manifest (reference only; the
#               portal has no modules, so this never fails the audit)
#   warnings -> known, honest data gaps (e.g. the 8 bundle pairs backed only by
#               data/reference/)
# Run it before any data change and after `make build-curriculum`.
audit: inventory

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
boot-check:
	PYTHONPATH=. python tools/ncosctl.py boot-check

list-modules:
	PYTHONPATH=. python tools/ncosctl.py list-modules

# ── Curriculum bundle (public/curriculum/) ──────────────────────────────────
# Builds the per-grade static JSON bundle the portal reads offline.
# Run this after any change to data/curriculum/ or data/lessons/.
build-curriculum:
	PYTHONPATH=. python scripts/build_app_curriculum.py

# The one-shot scripts under scripts/ are documentation as much as tools: a script
# that cannot import its own compatibility shim documents nothing (P2-8).
check-scripts:
	python3 scripts/check_scripts.py

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
