# M01 Chemistry Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用纯 Python 领域模型实现已冻结的 M01 六个顶层实体、ReactionParticipant 子实体及其实际使用的值对象。

**Architecture:** M01 独占 `chem_wiki.modules.chemistry_core`，并在该模块内按 identity、provenance、composition、实体和 Reaction 聚合的真实职责拆分文件。`chem_wiki.modules` 保持为隐式 namespace package，不承载共享领域类型；`chemistry_core` 包根 `__init__.py` 是未来跨模块消费者的唯一公共入口。标准库的不可变 dataclass、Enum、UUID 和 Decimal 表达领域数据与不变量；FastAPI、Pydantic、SQLAlchemy、化学库及 M02+ 能力留在边界之外。

**Tech Stack:** Python 3.13、标准库、pytest 9、Ruff；不新增依赖。

**Spec:** `docs/decisions/M01-chemistry-core-boundary.md`

## Global Constraints

- 只实现 `Element`、`Ion`、`Substance`、`Structure`、`FunctionalGroup`、`Reaction`，以及 Reaction 内的 `ReactionParticipant`。
- `ReactionParticipantId` 在所属 Reaction 生命周期内稳定；participant target 严格为 `SubstanceId | IonId`。
- `Condition` 是无 ID、无独立生命周期的内嵌值对象。
- 不实现 repository、service、Port、adapter、ORM mapping、migration、API 或任何 M02+ 类型。
- 不实现 `KnowledgeEdge`、`ContentSource`、`ContentRevision`、`Experiment`、`Phenomenon`、`Concept`、`Question`、`ExamTag` 或 `ExamOccurrence`。
- 不定义通用 `Entity`、`ChemicalSpecies`、`SourcedValue[T]` 或泛型 repository/service。
- `chemistry_core` 内部只能导入 Python 标准库和自己的内部模块；内部相互依赖优先使用相对导入。
- 后续模块只能从 `chem_wiki.modules.chemistry_core` 公共入口导入，不得依赖其内部文件。
- `backend/tests/modules/chemistry_core` 是 M01 自有测试，可按责任直接测试内部文件；公共边界另由 `test_public_boundary.py` 锁定。
- 不创建全局 `common`、`shared` 或通用 domain 包；`identifiers.py`、`provenance.py`、`composition.py` 只属于 M01。
- Structure 只保存库无关文本表示；不解析、不验证化学有效性、不计算指纹或官能团。
- 不创建 `AtomMapping`、`BondDiff`、`BondChange`、`Mechanism`、`MechanismStep`、`ElectronFlow` 或 `ElectronMove` 的 ID、接口、字段和占位类型。
- 每个任务遵循红—绿—重构；每个任务只在其完整子功能通过测试和 Ruff 后形成一个有意义的提交。

## File Map

```text
backend/src/chem_wiki/modules/
└── chemistry_core/                     # modules 保持为隐式 namespace package
    ├── __init__.py                     # M01 唯一公共入口，最终冻结导出类型
    ├── identifiers.py                  # 七种独立 UUID 强类型 ID
    ├── provenance.py                   # 最小外部来源引用
    ├── composition.py                  # Substance/Ion 共用的公式与组成项
    ├── element.py                      # Element 及其专用值对象
    ├── substance.py                    # Substance
    ├── ion.py                          # Ion 与 ElectricCharge
    ├── structure.py                    # Structure 与库无关表示值对象
    ├── functional_group.py             # FunctionalGroup 目录实体
    └── reaction.py                     # Reaction 聚合、Participant 与内嵌值对象

backend/tests/modules/chemistry_core/
├── test_identifiers_and_provenance.py
├── test_elements_substances_and_ions.py
├── test_structures_and_functional_groups.py
├── test_reaction.py
└── test_public_boundary.py
```

---

### Task 1: Strong IDs and minimal provenance

**Files:**
- Create: `backend/src/chem_wiki/modules/chemistry_core/__init__.py`
- Create: `backend/src/chem_wiki/modules/chemistry_core/identifiers.py`
- Create: `backend/src/chem_wiki/modules/chemistry_core/provenance.py`
- Test: `backend/tests/modules/chemistry_core/test_identifiers_and_provenance.py`

**Interfaces:**
- Consumes: Python `uuid.UUID` and `datetime.datetime` only.
- Produces: `ElementId`, `IonId`, `SubstanceId`, `StructureId`, `FunctionalGroupId`, `ReactionId`, `ReactionParticipantId`, `ProvenanceRef`.

- [ ] **Step 1: Write failing identity and provenance tests**

```python
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.identifiers import (
    ElementId,
    FunctionalGroupId,
    IonId,
    ReactionId,
    ReactionParticipantId,
    StructureId,
    SubstanceId,
)
from chem_wiki.modules.chemistry_core.provenance import ProvenanceRef


@pytest.mark.parametrize(
    "id_type",
    [ElementId, IonId, SubstanceId, StructureId, FunctionalGroupId, ReactionId, ReactionParticipantId],
)
def test_chemistry_core_ids_preserve_uuid_value(id_type: type) -> None:
    value = uuid4()
    assert id_type(value).value == value


def test_different_id_types_are_not_equal() -> None:
    value = uuid4()
    assert ElementId(value) != SubstanceId(value)


def test_chemistry_core_ids_are_immutable() -> None:
    identity = ElementId(uuid4())
    with pytest.raises(FrozenInstanceError):
        identity.value = uuid4()  # type: ignore[misc]


def test_provenance_requires_non_blank_source_id() -> None:
    with pytest.raises(ValueError, match="source_id"):
        ProvenanceRef(source_id=" ")


def test_provenance_keeps_optional_traceability_fields() -> None:
    retrieved_at = datetime(2026, 8, 20, tzinfo=UTC)
    provenance = ProvenanceRef(
        source_id="nist-webbook",
        source_url="https://example.test/source",
        citation="Example citation",
        retrieved_at=retrieved_at,
        source_version="2026-08",
    )
    assert provenance.retrieved_at == retrieved_at
```

- [ ] **Step 2: Run the tests and verify the red state**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_identifiers_and_provenance.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'chem_wiki.modules'`.

- [ ] **Step 3: Implement independent IDs and ProvenanceRef**

Use `@dataclass(frozen=True, slots=True)` for every type. Define all seven ID classes independently—do not add a shared entity-ID base class:

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ElementId:
    value: UUID


@dataclass(frozen=True, slots=True)
class IonId:
    value: UUID


@dataclass(frozen=True, slots=True)
class SubstanceId:
    value: UUID


@dataclass(frozen=True, slots=True)
class StructureId:
    value: UUID


@dataclass(frozen=True, slots=True)
class FunctionalGroupId:
    value: UUID


@dataclass(frozen=True, slots=True)
class ReactionId:
    value: UUID


@dataclass(frozen=True, slots=True)
class ReactionParticipantId:
    value: UUID
```

Implement the exact provenance contract and strip/validate `source_id` in `__post_init__`:

```python
@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    source_id: str
    source_url: str | None = None
    citation: str | None = None
    retrieved_at: datetime | None = None
    source_version: str | None = None

    def __post_init__(self) -> None:
        source_id = self.source_id.strip()
        if not source_id:
            raise ValueError("source_id must not be blank")
        object.__setattr__(self, "source_id", source_id)
```

- [ ] **Step 4: Verify green state and formatting**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_identifiers_and_provenance.py -q`

Expected: all tests PASS.

Run: `uv run --directory backend ruff check src/chem_wiki/modules/chemistry_core tests/modules/chemistry_core`

Expected: exit 0.

- [ ] **Step 5: Commit the M01 module foundation as one boundary**

```powershell
git add docs/decisions/M01-chemistry-core-boundary.md docs/superpowers/plans/2026-08-20-m01-chemistry-core.md backend/src/chem_wiki/modules/chemistry_core backend/tests/modules/chemistry_core/test_identifiers_and_provenance.py
git commit -m "feat(chemistry-core): establish module primitives"
```

---

### Task 2: Element, Substance, and Ion

**Files:**
- Create: `backend/src/chem_wiki/modules/chemistry_core/composition.py`
- Create: `backend/src/chem_wiki/modules/chemistry_core/element.py`
- Create: `backend/src/chem_wiki/modules/chemistry_core/substance.py`
- Create: `backend/src/chem_wiki/modules/chemistry_core/ion.py`
- Test: `backend/tests/modules/chemistry_core/test_elements_substances_and_ions.py`

**Interfaces:**
- Consumes: `ElementId`, `SubstanceId`, `IonId`, `ProvenanceRef`.
- Produces: `AtomicNumber`, `ElementSymbol`, `ChemicalFormula`, `CompositionEntry`, `ElectricCharge`, `Element`, `Substance`, `Ion`.

- [ ] **Step 1: Write failing value-object and entity tests**

Cover these exact behaviors:

```python
from decimal import Decimal
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.composition import ChemicalFormula, CompositionEntry
from chem_wiki.modules.chemistry_core.element import AtomicNumber, Element, ElementSymbol
from chem_wiki.modules.chemistry_core.identifiers import ElementId, IonId, SubstanceId
from chem_wiki.modules.chemistry_core.ion import ElectricCharge, Ion
from chem_wiki.modules.chemistry_core.substance import Substance


def test_element_keeps_stable_identity_and_names() -> None:
    element = Element(ElementId(uuid4()), AtomicNumber(17), ElementSymbol("Cl"), "氯", "chlorine")
    assert element.symbol.value == "Cl"


def test_element_names_must_not_be_blank() -> None:
    with pytest.raises(ValueError, match="name_zh"):
        Element(ElementId(uuid4()), AtomicNumber(17), ElementSymbol("Cl"), " ", "chlorine")


@pytest.mark.parametrize("value", [0, -1])
def test_atomic_number_must_be_positive(value: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        AtomicNumber(value)


@pytest.mark.parametrize("value", ["", "cl", "CL"])
def test_element_symbol_rejects_invalid_spelling(value: str) -> None:
    with pytest.raises(ValueError, match="symbol"):
        ElementSymbol(value)


def test_formula_is_opaque_but_not_blank() -> None:
    assert ChemicalFormula("NH4+").value == "NH4+"
    with pytest.raises(ValueError, match="formula"):
        ChemicalFormula(" ")


def test_composition_amount_must_be_positive() -> None:
    with pytest.raises(ValueError, match="amount"):
        CompositionEntry(ElementId(uuid4()), Decimal("0"))


def test_substance_requires_composition() -> None:
    with pytest.raises(ValueError, match="composition"):
        Substance(SubstanceId(uuid4()), ChemicalFormula("H2O"), ())


def test_ion_requires_nonzero_charge() -> None:
    with pytest.raises(ValueError, match="charge"):
        ElectricCharge(0)


def test_substance_and_ion_share_composition_without_a_species_base() -> None:
    entry = CompositionEntry(ElementId(uuid4()), Decimal("1"))
    substance = Substance(SubstanceId(uuid4()), ChemicalFormula("HCl"), (entry,))
    ion = Ion(IonId(uuid4()), ChemicalFormula("Cl-"), (entry,), ElectricCharge(-1))
    assert substance.composition == ion.composition
```

- [ ] **Step 2: Run the tests and verify the red state**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_elements_substances_and_ions.py -q`

Expected: FAIL because `composition`, `element`, `substance`, and `ion` modules do not exist.

- [ ] **Step 3: Implement the minimal immutable model**

Use these exact public shapes:

```python
@dataclass(frozen=True, slots=True)
class AtomicNumber:
    value: int  # __post_init__: value > 0


@dataclass(frozen=True, slots=True)
class ElementSymbol:
    value: str  # __post_init__: fullmatch r"[A-Z][a-z]{0,2}"


@dataclass(frozen=True, slots=True)
class ChemicalFormula:
    value: str  # strip and require non-blank; do not parse


@dataclass(frozen=True, slots=True)
class CompositionEntry:
    element_id: ElementId
    amount: Decimal  # require > 0
    provenance: tuple[ProvenanceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class ElectricCharge:
    value: int  # require != 0


@dataclass(frozen=True, slots=True)
class Element:
    id: ElementId
    atomic_number: AtomicNumber
    symbol: ElementSymbol
    name_zh: str
    name_en: str
    provenance: tuple[ProvenanceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class Substance:
    id: SubstanceId
    formula: ChemicalFormula
    composition: tuple[CompositionEntry, ...]  # require non-empty
    provenance: tuple[ProvenanceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class Ion:
    id: IonId
    formula: ChemicalFormula
    composition: tuple[CompositionEntry, ...]  # require non-empty
    charge: ElectricCharge
    provenance: tuple[ProvenanceRef, ...] = ()
```

Validate `name_zh` and `name_en` as stripped non-blank strings. Do not parse formulae, infer composition, add periodic-table lookup, or create a shared `ChemicalSpecies` class.

- [ ] **Step 4: Verify the focused model**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_elements_substances_and_ions.py -q`

Expected: all tests PASS.

Run: `uv run --directory backend ruff check src/chem_wiki/modules/chemistry_core tests/modules/chemistry_core`

Expected: exit 0.

- [ ] **Step 5: Commit the coherent chemical-identity subfeature**

```powershell
git add backend/src/chem_wiki/modules/chemistry_core/composition.py backend/src/chem_wiki/modules/chemistry_core/element.py backend/src/chem_wiki/modules/chemistry_core/substance.py backend/src/chem_wiki/modules/chemistry_core/ion.py backend/tests/modules/chemistry_core/test_elements_substances_and_ions.py
git commit -m "feat(chemistry-core): model elements substances and ions"
```

---

### Task 3: Structure and FunctionalGroup

**Files:**
- Create: `backend/src/chem_wiki/modules/chemistry_core/structure.py`
- Create: `backend/src/chem_wiki/modules/chemistry_core/functional_group.py`
- Test: `backend/tests/modules/chemistry_core/test_structures_and_functional_groups.py`

**Interfaces:**
- Consumes: `StructureId`, `SubstanceId`, `FunctionalGroupId`, `ProvenanceRef`.
- Produces: `StructureFormat`, `StructureText`, `Structure`, `FunctionalGroup`.

- [ ] **Step 1: Write failing representation and catalog tests**

```python
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.functional_group import FunctionalGroup
from chem_wiki.modules.chemistry_core.identifiers import FunctionalGroupId, StructureId, SubstanceId
from chem_wiki.modules.chemistry_core.structure import Structure, StructureFormat, StructureText


def test_structure_is_separate_and_keeps_opaque_text() -> None:
    structure = Structure(
        id=StructureId(uuid4()),
        substance_id=SubstanceId(uuid4()),
        format=StructureFormat("smiles"),
        text=StructureText("CCO"),
    )
    assert structure.text.value == "CCO"


@pytest.mark.parametrize("value", ["", " "])
def test_structure_format_and_text_reject_blank_values(value: str) -> None:
    with pytest.raises(ValueError):
        StructureFormat(value)
    with pytest.raises(ValueError):
        StructureText(value)


def test_functional_group_is_a_minimal_catalog_entity() -> None:
    group = FunctionalGroup(FunctionalGroupId(uuid4()), "hydroxyl")
    assert group.name == "hydroxyl"


def test_functional_group_name_must_not_be_blank() -> None:
    with pytest.raises(ValueError, match="name"):
        FunctionalGroup(FunctionalGroupId(uuid4()), " ")
```

- [ ] **Step 2: Run the tests and verify the red state**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_structures_and_functional_groups.py -q`

Expected: FAIL because `structure` and `functional_group` modules do not exist.

- [ ] **Step 3: Implement only storage-safe representations**

```python
@dataclass(frozen=True, slots=True)
class StructureFormat:
    value: str  # strip and require non-blank


@dataclass(frozen=True, slots=True)
class StructureText:
    value: str  # require non-blank; otherwise preserve verbatim


@dataclass(frozen=True, slots=True)
class Structure:
    id: StructureId
    substance_id: SubstanceId
    format: StructureFormat
    text: StructureText
    provenance: tuple[ProvenanceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class FunctionalGroup:
    id: FunctionalGroupId
    name: str  # strip and require non-blank
    provenance: tuple[ProvenanceRef, ...] = ()
```

Do not add SMILES validation, parser hooks, fingerprints, atom indices, structure comparison, functional-group matching, or chemistry-library imports.

- [ ] **Step 4: Verify the focused model**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_structures_and_functional_groups.py -q`

Expected: all tests PASS.

Run: `uv run --directory backend ruff check src/chem_wiki/modules/chemistry_core tests/modules/chemistry_core`

Expected: exit 0.

- [ ] **Step 5: Commit the structure catalog boundary**

```powershell
git add backend/src/chem_wiki/modules/chemistry_core/structure.py backend/src/chem_wiki/modules/chemistry_core/functional_group.py backend/tests/modules/chemistry_core/test_structures_and_functional_groups.py
git commit -m "feat(chemistry-core): add structure and functional group entities"
```

---

### Task 4: Reaction aggregate and participant invariants

**Files:**
- Create: `backend/src/chem_wiki/modules/chemistry_core/reaction.py`
- Test: `backend/tests/modules/chemistry_core/test_reaction.py`

**Interfaces:**
- Consumes: `ReactionId`, `ReactionParticipantId`, `SubstanceId`, `IonId`, `ProvenanceRef`.
- Produces: `ReactionCode`, `ReactionStatus`, `ParticipantTarget`, `ReactionRole`, `StoichiometricCoefficient`, `Phase`, `Condition`, `ReactionParticipant`, `Reaction`.

- [ ] **Step 1: Write failing tests for values and participant targets**

```python
from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

import pytest

from chem_wiki.modules.chemistry_core.identifiers import (
    IonId,
    ReactionId,
    ReactionParticipantId,
    SubstanceId,
)
from chem_wiki.modules.chemistry_core.reaction import (
    Condition,
    Phase,
    Reaction,
    ReactionCode,
    ReactionParticipant,
    ReactionRole,
    StoichiometricCoefficient,
)


def participant(role: ReactionRole, target: SubstanceId | IonId) -> ReactionParticipant:
    return ReactionParticipant(
        id=ReactionParticipantId(uuid4()),
        target=target,
        role=role,
        stoichiometry=StoichiometricCoefficient(Decimal("1")),
    )


def test_stoichiometry_must_be_positive() -> None:
    with pytest.raises(ValueError, match="stoichiometry"):
        StoichiometricCoefficient(Decimal("0"))


def test_condition_is_an_embedded_value_without_id() -> None:
    condition = Condition(kind="temperature", value=Decimal("298.15"), unit="K")
    assert not hasattr(condition, "id")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ReactionCode(" "),
        lambda: Phase(" "),
        lambda: Condition(kind=" "),
        lambda: Condition(kind="temperature", value=" "),
        lambda: Condition(kind="temperature", value="298", unit=" "),
    ],
)
def test_reaction_text_values_reject_blank_content(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="blank"):
        factory()


def test_participant_target_accepts_only_substance_or_ion_id() -> None:
    with pytest.raises(TypeError, match="target"):
        ReactionParticipant(
            ReactionParticipantId(uuid4()),
            "not-an-id",  # type: ignore[arg-type]
            ReactionRole.REACTANT,
            StoichiometricCoefficient(Decimal("1")),
        )
```

- [ ] **Step 2: Add failing aggregate invariant tests**

```python
def test_reaction_accepts_substance_reactant_and_ion_product() -> None:
    reactant = participant(ReactionRole.REACTANT, SubstanceId(uuid4()))
    product = participant(ReactionRole.PRODUCT, IonId(uuid4()))
    reaction = Reaction(ReactionId(uuid4()), ReactionCode("rxn-1"), (reactant, product))
    assert reaction.participants == (reactant, product)


@pytest.mark.parametrize(
    "roles, message",
    [((ReactionRole.PRODUCT,), "reactant"), ((ReactionRole.REACTANT,), "product")],
)
def test_reaction_requires_reactant_and_product(
    roles: tuple[ReactionRole, ...], message: str
) -> None:
    participants = tuple(participant(role, SubstanceId(uuid4())) for role in roles)
    with pytest.raises(ValueError, match=message):
        Reaction(ReactionId(uuid4()), ReactionCode("rxn-1"), participants)


def test_reaction_rejects_duplicate_participant_ids() -> None:
    shared_id = ReactionParticipantId(uuid4())
    reactant = ReactionParticipant(
        shared_id,
        SubstanceId(uuid4()),
        ReactionRole.REACTANT,
        StoichiometricCoefficient(Decimal("1")),
    )
    product = ReactionParticipant(
        shared_id,
        IonId(uuid4()),
        ReactionRole.PRODUCT,
        StoichiometricCoefficient(Decimal("1")),
    )
    with pytest.raises(ValueError, match="participant id"):
        Reaction(ReactionId(uuid4()), ReactionCode("rxn-1"), (reactant, product))
```

- [ ] **Step 3: Run the tests and verify the red state**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_reaction.py -q`

Expected: FAIL because `reaction` does not exist.

- [ ] **Step 4: Implement the complete M01 Reaction aggregate**

```python
class ReactionStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ReactionRole(StrEnum):
    REACTANT = "reactant"
    PRODUCT = "product"
    CATALYST = "catalyst"
    SOLVENT = "solvent"


type ParticipantTarget = SubstanceId | IonId


@dataclass(frozen=True, slots=True)
class ReactionCode:
    value: str  # strip and require non-blank


@dataclass(frozen=True, slots=True)
class StoichiometricCoefficient:
    value: Decimal  # require > 0


@dataclass(frozen=True, slots=True)
class Phase:
    value: str  # strip and require non-blank; do not freeze a phase taxonomy yet


@dataclass(frozen=True, slots=True)
class Condition:
    kind: str
    value: str | Decimal | None = None
    unit: str | None = None
    # strip/require kind; reject blank string value or unit


@dataclass(frozen=True, slots=True)
class ReactionParticipant:
    id: ReactionParticipantId
    target: ParticipantTarget
    role: ReactionRole
    stoichiometry: StoichiometricCoefficient
    phase: Phase | None = None
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.target, (SubstanceId, IonId)):
            raise TypeError("target must be SubstanceId or IonId")


@dataclass(frozen=True, slots=True)
class Reaction:
    id: ReactionId
    code: ReactionCode
    participants: tuple[ReactionParticipant, ...]
    conditions: tuple[Condition, ...] = ()
    status: ReactionStatus = ReactionStatus.DRAFT
    reversible: bool = False
    provenance: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        participant_ids = [participant.id for participant in self.participants]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participant id must be unique within a reaction")
        roles = {participant.role for participant in self.participants}
        if ReactionRole.REACTANT not in roles:
            raise ValueError("reaction requires at least one reactant")
        if ReactionRole.PRODUCT not in roles:
            raise ValueError("reaction requires at least one product")
```

Do not add equation balancing, conservation checks, publication transitions, equation text, reaction SMILES, atom mappings, bond changes, mechanisms, repositories, or services.

- [ ] **Step 5: Verify the aggregate**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_reaction.py -q`

Expected: all tests PASS.

Run: `uv run --directory backend ruff check src/chem_wiki/modules/chemistry_core tests/modules/chemistry_core`

Expected: exit 0.

- [ ] **Step 6: Commit the Reaction subfeature**

```powershell
git add backend/src/chem_wiki/modules/chemistry_core/reaction.py backend/tests/modules/chemistry_core/test_reaction.py
git commit -m "feat(chemistry-core): add reaction aggregate invariants"
```

---

### Task 5: Freeze the public API and dependency boundary

**Files:**
- Modify: `backend/src/chem_wiki/modules/chemistry_core/__init__.py`
- Test: `backend/tests/modules/chemistry_core/test_public_boundary.py`

**Interfaces:**
- Consumes: every public M01 type created in Tasks 1–4.
- Produces: the explicit `chem_wiki.modules.chemistry_core.__all__` boundary and an AST-based third-party dependency guard.

- [ ] **Step 1: Write the failing public-scope test**

```python
import chem_wiki.modules.chemistry_core as chemistry


EXPECTED_PUBLIC_TYPES = {
    "ElementId", "IonId", "SubstanceId", "StructureId", "FunctionalGroupId",
    "ReactionId", "ReactionParticipantId", "ProvenanceRef", "AtomicNumber",
    "ElementSymbol", "ChemicalFormula", "CompositionEntry", "ElectricCharge",
    "Element", "Substance", "Ion", "StructureFormat", "StructureText",
    "Structure", "FunctionalGroup", "ReactionCode", "ReactionStatus",
    "ParticipantTarget", "ReactionRole", "StoichiometricCoefficient", "Phase",
    "Condition", "ReactionParticipant", "Reaction",
}


def test_public_api_matches_frozen_m01_scope() -> None:
    assert set(chemistry.__all__) == EXPECTED_PUBLIC_TYPES
    assert all(hasattr(chemistry, name) for name in EXPECTED_PUBLIC_TYPES)
```

- [ ] **Step 2: Write the failing dependency-boundary test**

```python
import ast
import sys
from pathlib import Path


def test_chemistry_core_imports_only_stdlib_or_own_internals() -> None:
    module_root = (
        Path(__file__).parents[3] / "src" / "chem_wiki" / "modules" / "chemistry_core"
    )
    allowed_stdlib = set(sys.stdlib_module_names) | {"__future__"}
    violations: list[str] = []

    for path in module_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.level > 0:
                    continue
                modules = [node.module]
            else:
                continue
            for module in modules:
                root = module.partition(".")[0]
                is_own_module = module == "chem_wiki.modules.chemistry_core" or module.startswith(
                    "chem_wiki.modules.chemistry_core."
                )
                if root not in allowed_stdlib and not is_own_module:
                    violations.append(f"{path}:{module}")

    assert violations == []
```

- [ ] **Step 3: Run the tests and verify the red state**

Run: `uv run --directory backend pytest tests/modules/chemistry_core/test_public_boundary.py -q`

Expected: public API test FAIL because `chemistry.__all__` is not yet defined; the dependency test must PASS.

- [ ] **Step 4: Add explicit imports and the exact __all__ list**

Import every name in `EXPECTED_PUBLIC_TYPES` from its owning module and define `__all__` with exactly those strings. Do not export modules, helper functions, deferred entities, repository interfaces, or framework DTOs.

```python
__all__ = [
    "AtomicNumber",
    "ChemicalFormula",
    "CompositionEntry",
    "Condition",
    "ElectricCharge",
    "Element",
    "ElementId",
    "ElementSymbol",
    "FunctionalGroup",
    "FunctionalGroupId",
    "Ion",
    "IonId",
    "ParticipantTarget",
    "Phase",
    "ProvenanceRef",
    "Reaction",
    "ReactionCode",
    "ReactionId",
    "ReactionParticipant",
    "ReactionParticipantId",
    "ReactionRole",
    "ReactionStatus",
    "StoichiometricCoefficient",
    "Structure",
    "StructureFormat",
    "StructureId",
    "StructureText",
    "Substance",
    "SubstanceId",
]
```

- [ ] **Step 5: Run focused and regression validation**

Run: `uv run --directory backend pytest tests/modules/chemistry_core tests/test_health.py -q`

Expected: all M01 domain tests and the existing health test PASS. The database integration test is intentionally excluded because M01 adds no persistence behavior and it requires a running PostgreSQL instance.

Run: `uv run --directory backend ruff check .`

Expected: exit 0.

Run: `uv run --directory backend ruff format --check .`

Expected: exit 0.

- [ ] **Step 6: Review scope and commit the frozen public boundary**

Run: `git diff --name-only HEAD`

Expected: only the files listed in this plan; no `api`, `infrastructure`, `migrations`, `pyproject.toml`, or lockfile changes.

```powershell
git add backend/src/chem_wiki/modules/chemistry_core/__init__.py backend/tests/modules/chemistry_core/test_public_boundary.py
git commit -m "test(chemistry-core): lock the M01 public boundary"
```

## Focused Test Strategy

- 值对象：逐一验证合法构造、空白/范围错误、不可变性和强类型 ID 不串用。
- 实体：验证稳定身份、仅保存冻结字段、provenance 可附着到事实或参与关系。
- Reaction：重点覆盖 participant target 联合、正计量系数、participant ID 唯一性、至少一个 reactant/product、Condition 无 ID。
- 架构：AST 守卫只允许标准库与 M01 自身内部导入；精确 `__all__` 将 `chem_wiki.modules.chemistry_core` 冻结为未来跨模块消费者的唯一入口。
- 回归：每个任务运行自身测试；收口运行全部 M01 测试、现有 health 测试和 Ruff。纯领域变更不启动 PostgreSQL，也不触碰前端。
