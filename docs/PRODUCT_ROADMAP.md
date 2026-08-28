# Chem Wiki Product Roadmap

## Outcome

Chem Wiki is a connected high-school chemistry exploration system. Learners move continuously between elements, species, structures, reactions, experimental phenomena, and concepts instead of using isolated demo pages.

The product should make the existing chemistry data foundation visible through three connected exploration loops:

1. **Element exploration** — Periodic Table → Element Wiki → ions/substances → reactions/concepts → Equation Lab.
2. **Reaction exploration** — species → known reaction → equation/conditions/phenomena/concepts → related elements/structures.
3. **Structure exploration** — species → structure → functional groups → related properties/reactions → Equation Lab.

Mechanism/step animation work follows these connected product loops rather than preceding them.

## Master

The current product baseline is the working M00–M07 implementation on `main`, including:

- React + FastAPI + PostgreSQL application foundation;
- Chemistry Core identities and frozen public contracts;
- 118-element Periodic Table and M02 element data/provenance pipeline;
- Element Wiki read-model boundary;
- EquationDraft, phase, drag/reorder/move, Undo/Redo, copy, molecular/ionic/net-ionic balance;
- consolidated `knowledge_catalog` application boundary;
- known Reaction matching, direction/orientation, completion and deterministic ranking;
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

Existing module contracts remain stable unless a later product requirement proves that a public boundary must change.

## Integration strategy

Development is integration-first.

Before creating a new implementation, inspect:

1. existing repository capability;
2. existing installed dependency;
3. existing data projection/index not yet consumed;
4. mature open-source solution;
5. remaining product-specific code.

A new dependency is justified when it removes substantial low-value custom implementation or unlocks a connected product flow with acceptable license, maintenance, security, runtime and bundle cost.

### Current mature OSS owners

| Responsibility | Canonical tool | Status |
| --- | --- | --- |
| molecule sketch/edit | Ketcher | integrated |
| chemistry/structure computation | RDKit | integrated |
| interactive small-molecule 3D | 3Dmol.js | integrated |
| local knowledge-graph rendering/layout | Cytoscape.js (+ fCoSE when useful) | next integration phase |
| standard chemistry/equation typesetting | KaTeX + mhchem | next reaction-experience phase |

Do not add a second molecule editor, second chemistry engine, or second 3D viewer while the current owners satisfy the requirement.

## Phase 1 — Product integration reset

**Goal:** make the existing data foundation visible through a complete Element exploration loop.

### Element properties

- make normal local data setup publish supported PubChem snapshot properties through the existing M02 source → claim → publication → property pipeline;
- retain NIST as the preferred owner where the current policy selects a higher-quality first-ionization value;
- make Periodic Table electronegativity and first-ionization views show real application data for supported elements.

### Element Wiki

Replace placeholder/empty related sections with bounded application read data:

- core/common ions;
- core/common substances;
- high-priority reactions involving those species;
- reviewed directly related concepts and phenomena where available.

Use deterministic ranking and limits so the page remains a learning surface rather than a raw database dump.

### Knowledge graph

Use Cytoscape.js for the Element Wiki local graph. The backend owns graph semantics and returns typed nodes/edges; Cytoscape owns interactive rendering and layout.

The graph must lead somewhere:

- Reaction → Equation Lab using canonical Reaction data;
- Species with an accepted Structure link → existing Structure Lab;
- Concept/Phenomenon → reviewed content detail.

### Structure entry

Allow Structure Lab to receive a known catalog species/accepted Structure link and converge on the existing Ketcher + RDKit + 3Dmol surface. Manual SMILES input remains available but is no longer the only entry path.

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

## Phase 2 — Reaction experience

**Goal:** turn Equation Lab from a balance/editor surface into a connected reaction-learning surface.

Planned product work:

- Builder composition completion backed by `knowledge_catalog`, not exact-ion echo;
- implicit magnetic drop zones;
- Edit ↔ Settled equation states;
- KaTeX + mhchem standard equation rendering;
- visible canonical reaction conditions, phenomena, type and concepts;
- navigation from a reaction to related species, elements and available structures.

M05 EquationDraft remains the interaction/history anchor. Canonical Reaction completion remains a projection rather than a second draft owner.

## Phase 3 — Structure experience

**Goal:** make catalog-backed structure exploration part of normal chemistry navigation.

Use accepted Structure links and the existing Ketcher/RDKit/3Dmol/FunctionalGroup stack to expose:

- 2D and 3D structure;
- functional groups;
- related species and transformations;
- related known reactions;
- transitions into Equation Lab.

## Phase 4 — Reaction process / mechanism

Mechanism work begins after the product can already navigate Reaction ↔ Species ↔ Structure.

This phase may add reviewed bond changes, mechanism steps, electron-flow representations and animation where the data/model supports them. Mechanism truth remains separate from balance or atom-mapping inference.

## Documentation ownership

- `docs/PRODUCT_ROADMAP.md` — canonical product direction, integration strategy and current phases.
- `docs/handoffs/Mxx.md` — current implemented module capability and public boundary.
- `docs/decisions/` — durable architecture decisions whose scope is narrower than this roadmap.
- `README.md` — concise current product entry point and local setup.

Update these owners in place as capabilities change. Git preserves history.
