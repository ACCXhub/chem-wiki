# Chem Wiki Product Roadmap

## Outcome

Chem Wiki is a connected high-school chemistry exploration system. Learners move continuously between elements, species, structures, reactions, experimental phenomena, and concepts instead of using isolated demo pages.

The product exposes the existing chemistry foundation through three connected exploration loops:

1. **Element exploration** — Periodic Table → Element Wiki → ions/substances → reactions/concepts → Equation Lab.
2. **Reaction exploration** — species → known reaction → equation/conditions/phenomena/concepts → related elements/structures.
3. **Structure exploration** — species → structure → functional groups → related properties/reactions → Equation Lab.

Reaction-process/mechanism work follows these connected loops rather than preceding them.

## Master

The current product baseline is the working M00–M07 implementation on `main`, including:

- React + FastAPI + PostgreSQL application foundation;
- Chemistry Core identities and frozen public contracts;
- 118-element Periodic Table and M02 element data/provenance pipeline;
- Element Wiki read-model boundary;
- EquationDraft, phase, drag/reorder/move, Undo/Redo, copy, molecular/ionic/net-ionic balance;
- consolidated `knowledge_catalog` application boundary;
- known Reaction matching, direction/orientation, completion and deterministic ranking;
- catalog-backed Builder composition completion and Reaction learning detail;
- KaTeX + mhchem chemistry/equation display with Reaction → Element / Structure navigation;
- Structure Lab with Ketcher, RDKit and 3Dmol.js;
- FunctionalGroup detection;
- compact Equation Lab species palette and Builder interaction.

The current consolidated chemistry release provides approximately:

- 309 species;
- 183 reactions;
- 69 accepted Structure links;
- 309 teaching projections;
- 637 non-species knowledge records;
- reviewed rules and curriculum projections.

## Locked architecture

Chemistry facts keep one canonical data path:

```text
chem-knowledge-data consolidated release
        ↓
knowledge_catalog / element_data
        ↓
module read models
        ↓
React product surfaces
```

The frontend presents chemistry but does not become another chemistry-data owner.

Third-party projects own bounded technical responsibilities only. They do not become owners of canonical species, reactions, element properties, or learning semantics.

Existing module contracts remain stable unless a product requirement proves that a public boundary must change.

## Integration strategy

Development is integration-first.

Before creating a new implementation, inspect in order:

1. existing repository capability;
2. existing installed dependency;
3. existing data projection/index not yet consumed;
4. mature open-source solution;
5. remaining product-specific code.

A new dependency is justified when it removes substantial low-value custom implementation or unlocks a connected product flow with acceptable license, maintenance, security, runtime and bundle cost.

Curated lists such as `hsiaoyi0504/awesome-cheminformatics` are discovery indexes, not an approval list. Every candidate must be rechecked against its current upstream repository, maintenance status, license, platform cost and overlap with existing owners before adoption.

### Chemistry capability owners

| Responsibility | Tool / owner | Status | Decision |
| --- | --- | --- | --- |
| canonical chemistry facts | `chem-knowledge-data` + application catalog modules | integrated | product truth owner |
| molecule sketch/edit | Ketcher | integrated | keep |
| chemistry/structure computation | RDKit | integrated | keep as primary structure engine |
| interactive small-molecule 3D | 3Dmol.js | integrated | keep |
| local knowledge-graph rendering/layout | Cytoscape.js | integrated | Element Wiki interactive concentric graph |
| standard chemistry/equation typesetting | KaTeX + mhchem | integrated | narrow display adapter; canonical DTOs remain truth |

### Evaluate before custom chemistry computation

These projects are candidates for specific gaps, not dependencies to install by default:

| Candidate | Potential role | Current decision |
| --- | --- | --- |
| ChemPy | formula parsing, stoichiometry cross-checks, equilibria, kinetics and physical/inorganic calculations | high-priority evaluation before extending calculation features; do not replace stable M05 balance without a demonstrated gain |
| ChEMBL Structure Pipeline | RDKit-based molecule validation/standardisation during structure-data ingestion | evaluate only if current structure import/normalisation produces a real consistency gap |
| OPSIN | systematic IUPAC name → structure conversion | evaluate only when name-to-structure becomes a product requirement; account for Java/runtime cost |
| Open Babel | broad chemical-format conversion | fallback only when RDKit/Ketcher format coverage is insufficient; GPL-2.0 distribution implications must be reviewed first |
| CGRtools | reaction/condensed reaction-graph processing | research reference for future reaction-process work; current main upstream is not active enough to treat as a planned dependency |

Projects with substantial overlap with existing owners, such as a second molecule editor or second general structure engine, are not added merely because they appear in an ecosystem list.

## Skill strategy

Project-specific custom Codex skills stay deliberately small:

- `task-anchor` — iterative Outcome/Master/Locked/Delta/Deliverables continuity;
- `convergent-editing` — one canonical current repository/artifact state;
- `compact-product-ui` — dense, polished learner-facing product UI;
- `integration-first` — repository/dependency/data/OSS audit before new capability work.

Debugging, TDD, verification, React performance and similar framework skills are used from the system/framework when relevant rather than copied into the project skill repository.

## Phase 1 — Product integration reset（已实现）

**Goal:** make the existing data foundation visible through a complete Element exploration loop.

### Element properties

- normal local data setup publishes the versioned PubChem snapshot through the existing M02 source → claim → publication → property pipeline;
- NIST remains the preferred publication where the current policy has a higher-quality first-ionization value;
- Periodic Table electronegativity and first-ionization views consume the published application read model.

### Element Wiki

The Element Wiki exposes bounded, deterministic application read data:

- core/common ions;
- core/common substances;
- high-priority reactions involving those species;
- reviewed directly related concepts and phenomena where available.

The neighborhood is limited to four ions, six substances, six reactions, three concepts and three phenomena.

### Knowledge graph

Cytoscape.js renders the Element Wiki local graph. The backend owns graph semantics and returns typed nodes/edges; Cytoscape owns interactive rendering, concentric layout and selection.

The graph must lead somewhere:

- Reaction → Equation Lab using canonical Reaction data;
- Species with an accepted Structure link → existing Structure Lab;
- Concept/Phenomenon → reviewed content detail.

### Structure entry

Structure Lab accepts a known catalog species/accepted Structure link, loads its canonical SMILES and converges on the existing Ketcher + RDKit + 3Dmol surface. Manual SMILES input remains available but is no longer the only entry path.

### Periodic Table presentation

- retain the 118-element layout;
- align the metal/nonmetal staircase to actual grid tracks/gaps;
- preserve usable heatmaps, inspector and search;
- ensure floating lab navigation does not cover element cells or scrollbars.

### Product copy

Learner-facing UI uses chemistry, actions and meaningful state. Milestone IDs, database/canonical-owner explanations and implementation policy language belong in engineering documentation rather than primary learning surfaces.

### Phase 1 acceptance

- common supported elements expose real published properties;
- Fe/Al/Na/Cl/S Element Wiki pages expose non-empty related chemistry when the catalog contains it;
- Element Wiki contains a real interactive graph;
- Reaction nodes open the existing reaction/equation workflow;
- structured Species open the existing Structure Lab with known structure data;
- desktop and narrow mobile layouts remain usable;
- README and affected handoffs match the implemented state.

## Phase 2A — Reaction experience foundation（已实现）

**Goal:** turn Equation Lab from a balance/editor surface into a connected reaction-learning surface.

Implemented product work:

- Builder composition completion backed by `knowledge_catalog`, not exact-ion echo;
- KaTeX + mhchem standard equation rendering;
- visible canonical reaction conditions, phenomena, type and concepts;
- navigation from a reaction to related species, elements and available structures.

`knowledge_catalog` owns the durable learner-facing source-attribution projection imported from the pinned reviewed release. The application does not expose internal source IDs or require the external data checkout at request time.

M05 EquationDraft remains the interaction/history anchor. Canonical Reaction completion and learning detail remain read projections rather than a second draft owner.

## Phase 2B — Reaction interaction refinement（计划）

Planned product work:

- implicit magnetic drop zones;
- Edit ↔ Settled equation states.

Before extending calculation responsibilities beyond the stable M05 core, evaluate ChemPy against the exact gap. Reuse it only where it removes meaningful custom chemistry computation and can live behind a narrow backend adapter.

## Phase 3 — Structure experience

**Goal:** make catalog-backed structure exploration part of normal chemistry navigation.

Use accepted Structure links and the existing Ketcher/RDKit/3Dmol/FunctionalGroup stack to expose:

- 2D and 3D structure;
- functional groups;
- related species and transformations;
- related known reactions;
- transitions into Equation Lab.

If structure-data normalisation becomes a demonstrated ingestion problem, evaluate ChEMBL Structure Pipeline before writing another standardiser. If systematic-name parsing becomes a demonstrated user need, evaluate OPSIN before custom parsing.

## Phase 4 — Reaction process / mechanism

Mechanism work begins after the product can already navigate Reaction ↔ Species ↔ Structure.

This phase may add reviewed bond changes, mechanism steps, electron-flow representations and animation where the data/model supports them. Before adding custom reaction-processing infrastructure, audit RDKit's current reaction capabilities and current maintained OSS. CGRtools may inform the design, but its current upstream state does not make it an approved dependency.

Mechanism truth remains separate from balance or atom-mapping inference.

## Documentation ownership

- `docs/PRODUCT_ROADMAP.md` — canonical product direction, integration strategy, chemistry OSS registry and current phases.
- `docs/handoffs/Mxx.md` — current implemented module capability and public boundary.
- `docs/decisions/` — durable architecture decisions whose scope is narrower than this roadmap.
- `README.md` — concise current product entry point and local setup.

Update these owners in place as capabilities change. Git preserves history.
