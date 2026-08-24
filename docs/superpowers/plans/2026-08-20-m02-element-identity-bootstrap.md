# M02 Element Identity Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap exactly 118 canonical Elements from separately attributed Chinese seed claims and IUPAC identity claims, then prove idempotent PostgreSQL re-import and PubChem enrichment.

**Architecture:** Versioned factual JSON artifacts sit behind source-specific loaders. A narrow identity importer validates the joined 1–118 dataset, creates each canonical row together with four claims and four published selections in one transaction, and reuses the existing six-table M02 persistence contract. PubChem remains a separate enrichment importer and cannot publish identity fields.

**Tech Stack:** Python 3.13, SQLAlchemy 2, PostgreSQL 17, Alembic, pytest, Ruff.

**Spec:** `docs/decisions/M02-element-persistence-contract.md`

## Global Constraints

- Keep M01 `ElementId` as the canonical UUID and use only M01's public package exports.
- Attribute Periodic Table PRO only to its 116 non-empty `name_zh` values.
- Attribute `鿬` and `鿫` only to the approved official Chinese terminology source.
- Publish `atomic_number`, `symbol`, and `name_en` only from IUPAC claims.
- Store only factual seed fields plus citation/version/hash metadata; do not vendor source PDFs, code, Wiki prose, artwork, or visual assets.
- Do not add a generic resolver, NIST, M03 work, migrations, APIs, or background jobs.
- Do not commit in this task.

---

### Task 1: Auditable source loaders

**Files:**
- Create: `backend/src/chem_wiki/modules/element_data/seeds/iupac-periodic-table-2022-05-04.json`
- Create: `backend/src/chem_wiki/modules/element_data/seeds/periodic-table-pro-4b0446c.json`
- Create: `backend/src/chem_wiki/modules/element_data/seeds/official-chinese-elements-117-118.json`
- Create: `backend/src/chem_wiki/modules/element_data/iupac.py`
- Create: `backend/src/chem_wiki/modules/element_data/periodic_table_pro.py`
- Create: `backend/src/chem_wiki/modules/element_data/official_chinese_names.py`
- Create: `backend/tests/modules/element_data/test_identity_sources.py`

**Interfaces:**
- Produces: source-specific immutable records containing `record_key`, source metadata, content hash, retrieval time, raw factual fields, and normalized claims.

- [ ] **Step 1: Write failing source tests** asserting IUPAC covers literal atomic numbers `1..118`, Periodic Table PRO covers exactly 116 Chinese names and excludes 117/118, and the official supplement is exactly `{117: "鿬", 118: "鿫"}` with independent provenance.
- [ ] **Step 2: Run `uv run pytest tests/modules/element_data/test_identity_sources.py -q`** and confirm failure is caused by missing loaders.
- [ ] **Step 3: Add minimal factual artifacts and loaders** that validate metadata hashes, source-specific schemas, M01 identity values, and uniqueness without exposing source schema downstream.
- [ ] **Step 4: Re-run the focused test** and confirm it passes.

### Task 2: PostgreSQL identity bootstrap

**Files:**
- Create: `backend/src/chem_wiki/modules/element_data/identity_bootstrap.py`
- Create: `backend/tests/integration/test_element_identity_bootstrap.py`
- Modify: `backend/src/chem_wiki/modules/element_data/__init__.py`

**Interfaces:**
- Consumes: the three source loaders from Task 1 and existing `ElementDataBase` tables.
- Produces: `bootstrap_element_identities(session, ...) -> IdentityBootstrapResult`.

- [ ] **Step 1: Write failing PostgreSQL tests** asserting 118 unique canonical rows, 118 IUPAC records, 118 Chinese-name records split 116/2 by source, 472 claims, 472 current publications, correct source chains, and M01-valid `ElementId` values.
- [ ] **Step 2: Run the focused integration test** against migrated PostgreSQL and confirm failure is caused by the absent importer.
- [ ] **Step 3: Implement the minimal importer** using `atomic_number` lookup, one-time UUID creation, immutable evidence upserts, IUPAC authority publication for three fields, and source-correct Chinese-name publication.
- [ ] **Step 4: Re-run the focused integration test** and confirm it passes.

### Task 3: Full re-import and PubChem preservation

**Files:**
- Modify: `backend/tests/integration/test_element_identity_bootstrap.py`

**Interfaces:**
- Consumes: `bootstrap_element_identities` and existing `import_pubchem_elements`.
- Produces: executable evidence that the complete pipeline preserves identity.

- [ ] **Step 1: Add failing assertions** that a second full bootstrap creates no rows or claims, leaves all 118 UUIDs unchanged, and PubChem enrichment of hydrogen changes only approved property publications.
- [ ] **Step 2: Run the focused integration test** and confirm the new assertions fail for the intended missing behavior.
- [ ] **Step 3: Add only the importer behavior needed for idempotency** while retaining old claims and current selections.
- [ ] **Step 4: Run focused unit/integration tests, full backend pytest, `uv run ruff check .`, `uv run ruff format --check .`, Alembic upgrade/drift checks, and a real PostgreSQL ETL verification.**
