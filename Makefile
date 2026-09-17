.PHONY: install inventory audit check dev build lint preview boot-check list-modules build-curriculum validate-curriculum generate-schemes generate-records package-books

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

# ── Everything that must pass before a deploy ───────────────────────────────
# The app build is included so that "yarn build fails" cannot be discovered for
# the first time in production.
check: lint validate-curriculum
	$(YARN) build

# ── Dataset audit (expected to be red until the gaps below are closed) ──────
# `make inventory` reports real, known gaps: the math module's id (`math`)
# matches zero indicators (`mathematics`), 12 modules still have a stub
# validate(), and 9 subject-grades exist only in data/reference/. Deliberately
# unforgiving — do not relax it to make the output green.
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

validate-curriculum:
	PYTHONPATH=. python scripts/validate_app_curriculum.py

# ── Document generation (local, outputs to dist/) ──────────────────────────
generate-schemes:
	PYTHONPATH=. python scripts/generate_schemes.py --per-term

generate-records:
	PYTHONPATH=. python scripts/generate_records_of_work.py --per-term

package-books:
	PYTHONPATH=. python scripts/package_books.py
