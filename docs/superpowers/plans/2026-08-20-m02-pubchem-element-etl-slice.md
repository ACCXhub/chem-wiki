# M02 PubChem Element ETL Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one deterministic, PubChem-backed Element ETL slice that retains source evidence, publishes only approved supplemental properties, and is idempotent in PostgreSQL.

**Architecture:** A PubChem-only adapter owns the PUG REST table schema and returns immutable raw records. A source-neutral normalizer validates M01 identity values and emits frozen M02 claims; a narrow PostgreSQL importer matches an already-authoritatively-seeded `element` by `atomic_number`, persists evidence, selects only PubChem-approved supplemental fields, and updates canonical properties in the same transaction. PubChem cannot create a canonical identity because the frozen authority policy reserves identity/name calibration for IUPAC; a missing canonical element is therefore an explicit error.

**Tech Stack:** Python 3.13, standard-library HTTP/JSON, SQLAlchemy 2, PostgreSQL 17, Alembic, pytest, Ruff

**Spec:** `docs/decisions/M02-element-persistence-contract.md`

## Global Constraints

- Keep all source-specific payload and column handling behind the PubChem adapter.
- Use only the public `chem_wiki.modules.chemistry_core` surface from M01.
- Publish only `electronegativity`, `first_ionization_energy`, and `atomic_radius` from PubChem under authority policy `m02-pubchem-v1`.
- Do not create canonical elements from PubChem; `atomic_number`, `symbol`, and `name_en` remain validated evidence but are not selected values.
- Preserve raw evidence, field-level claims, immutable prior evidence, and the existing `ElementId` UUID.
- Normal tests inject the HTTP response; the separately marked live smoke is the only test allowed to use the network.
- Do not add adapters, workflow engines, generic ETL/repository abstractions, APIs, UI, background jobs, or M03+ work.
- Do not commit in this task.

---

### Task 1: PubChem adapter and source-neutral normalization

**Files:**
- Create: `backend/src/chem_wiki/modules/element_data/pubchem.py`
- Create: `backend/src/chem_wiki/modules/element_data/etl.py`
- Modify: `backend/src/chem_wiki/modules/element_data/__init__.py`
- Create: `backend/tests/modules/element_data/test_pubchem_etl.py`

**Interfaces:**
- Consumes: injectable `fetch_json(url: str, timeout: float) -> Mapping[str, object]`, public M01 `AtomicNumber` and `ElementSymbol`.
- Produces: `PubChemAdapter.fetch_elements(atomic_numbers) -> tuple[PubChemRawRecord, ...]`, `normalize_pubchem_record(record) -> NormalizedElementRecord`, and literal PubChem publication policy fields.

- [x] Write deterministic tests using a complete two-row PUG REST fixture. Assert filtering, source URL/version/hash stability, numeric normalization and units (`Pauling`, `pm`, `eV`), missing-value omission, malformed row rejection, and that identity claims are validated but excluded from publication.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/modules/element_data/test_pubchem_etl.py -v` and verify RED because the adapter and normalizer do not exist.
- [x] Implement the smallest PubChem adapter, injected HTTP boundary, immutable raw/normalized records, M01-backed identity validation, and literal publication allowlist required by the tests.
- [x] Re-run the focused test and verify GREEN; refactor only while it stays green.

### Task 2: Idempotent PostgreSQL evidence and publication upsert

**Files:**
- Create: `backend/src/chem_wiki/modules/element_data/pubchem_import.py`
- Modify: `backend/src/chem_wiki/modules/element_data/__init__.py`
- Create: `backend/tests/integration/test_pubchem_element_etl.py`

**Interfaces:**
- Consumes: `NormalizedElementRecord`, the six frozen SQLAlchemy tables, and a caller-owned SQLAlchemy `Session` transaction.
- Produces: `import_pubchem_records(session, records) -> PubChemImportResult`; it leaves commit/rollback ownership with the caller.

- [x] Write a PostgreSQL integration test that migrates the six-table schema, seeds one canonical Hydrogen identity with non-PubChem provenance, imports the real PubChem fixture, and asserts raw/source evidence, verified field claims, selected PubChem provenance, and canonical property values.
- [x] Add assertions that a second identical import preserves the `ElementId`, source-record/claim/publication counts, and `selected_at`; add a missing-canonical-element test that fails explicitly rather than publishing PubChem identity.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/integration/test_pubchem_element_etl.py -v -m integration` and verify RED because the importer does not exist.
- [x] Implement PostgreSQL `ON CONFLICT` operations for the source registry, immutable source record, immutable claims, current publication, and property materialization. Make identical current selections no-ops and update property/publication together when evidence changes.
- [x] Re-run the focused PostgreSQL test and verify GREEN; run the existing M02 migration tests to prove trigger compatibility.

### Task 3: Separate live smoke and final verification

**Files:**
- Create: `backend/tests/live/test_pubchem_live.py`
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Consumes: the real official endpoint `https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON` through `PubChemAdapter`.
- Produces: an opt-in `live` test for Hydrogen and Helium; HTTP 503 is reported as the documented transient throttling condition, not treated as deterministic-test success.

- [x] Write the opt-in live test first and verify RED because the `live` marker/adapter behavior is incomplete.
- [x] Add the `live` marker and minimal skip gate (`CHEM_WIKI_RUN_LIVE_PUBCHEM=1`); exercise real fields only when explicitly enabled.
- [x] Run the enabled live smoke once and record either returned Hydrogen/Helium fields plus throttling headers or the official transient 503 result.
- [x] Run focused unit/integration tests, all backend tests excluding live, `.\.venv\Scripts\ruff.exe check .`, `.\.venv\Scripts\ruff.exe format --check .`, and Alembic drift/round-trip checks; fix only regressions introduced by this slice.
