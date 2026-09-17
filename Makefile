.PHONY: install inventory check boot-check list-modules build-curriculum validate-curriculum

# ── Python environment ──────────────────────────────────────────────────────
# These targets are for local data pipeline work only.
# The app (app/) is a React + Vite project — use `cd app && npm run dev` there.

install:
	pip install -r requirements.txt

# ── Dataset inventory + agreement checks ────────────────────────────────────
# Derives every headline number in README.md / docs/DATA_MODEL.md from the data
# itself, and fails if the app cannot serve part of the dataset.
# Read-only: never writes to data/ except data/inventory.json.
inventory:
	PYTHONPATH=. python scripts/build_inventory.py

# Everything that must pass before a deploy. The app build is included so that
# "npm run build fails" cannot be discovered for the first time in production.
check: validate-curriculum inventory
	cd app && npm run build

# ── Kernel / module health ──────────────────────────────────────────────────
boot-check:
	PYTHONPATH=. python tools/ncosctl.py boot-check

list-modules:
	PYTHONPATH=. python tools/ncosctl.py list-modules

# ── Curriculum bundle (app/public/curriculum/) ─────────────────────────────
# Builds the per-grade static JSON bundle the React app reads offline.
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
