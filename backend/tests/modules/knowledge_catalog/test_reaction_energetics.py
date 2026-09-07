from decimal import Decimal
from uuid import UUID

from chem_wiki.modules.knowledge_catalog.reaction_energetics import (
    PhaseFormationEnthalpy,
    derive_standard_reaction_enthalpy,
)
from chem_wiki.modules.knowledge_catalog.read_model import (
    CatalogReactionParticipantResult,
    CatalogReactionResult,
    CatalogSourceAttributionResult,
)

HYDROGEN_ID = UUID("00000000-0000-0000-0000-000000000001")
OXYGEN_ID = UUID("00000000-0000-0000-0000-000000000002")
WATER_ID = UUID("00000000-0000-0000-0000-000000000003")
SOURCE = CatalogSourceAttributionResult(name="Cantera NASA thermochemistry", url=None)


def _participant(
    *,
    role: str,
    coefficient: int,
    species_id: str,
    application_id: UUID,
    name_zh: str,
    formula: str,
    phase: str,
) -> CatalogReactionParticipantResult:
    return CatalogReactionParticipantResult(
        role=role,
        coefficient=coefficient,
        species_id=species_id,
        application_target_id=application_id,
        target_type="substance",
        non_species_ref=None,
        source_species_ref=species_id,
        formula_literal=None,
        phase=phase,
        name_zh=name_zh,
        formula=formula,
        charge=0,
    )


def _hydrogen_combustion() -> CatalogReactionResult:
    return CatalogReactionResult(
        consolidated_id="reaction:inorganic:reaction:hydrogen-combustion",
        application_reaction_id=UUID("00000000-0000-0000-0000-000000000010"),
        source_package="inorganic",
        source_id="reaction:hydrogen-combustion",
        name_zh="氢气燃烧",
        materialization_state="materialized",
        not_materialized_reasons=[],
        participants=[
            _participant(
                role="reactant",
                coefficient=2,
                species_id="species:hydrogen",
                application_id=HYDROGEN_ID,
                name_zh="氢气",
                formula="H2",
                phase="g",
            ),
            _participant(
                role="reactant",
                coefficient=1,
                species_id="species:oxygen",
                application_id=OXYGEN_ID,
                name_zh="氧气",
                formula="O2",
                phase="g",
            ),
            _participant(
                role="product",
                coefficient=2,
                species_id="species:water",
                application_id=WATER_ID,
                name_zh="水",
                formula="H2O",
                phase="l",
            ),
        ],
        reaction_types=["燃烧反应"],
        conditions=["点燃"],
        equation="2H2(g) + O2(g) -> 2H2O(l)",
        equation_status="balanced",
        reversible=False,
        provenance_refs=["catalog:test"],
    )


def _formation_enthalpy(
    species_id: str,
    phase: str,
    value: str,
) -> PhaseFormationEnthalpy:
    return PhaseFormationEnthalpy(
        species_id=species_id,
        phase=phase,
        temperature_k=Decimal("298.15"),
        standard_pressure_bar=Decimal("1.0"),
        delta_f_h_kj_mol=Decimal(value),
        sources=(SOURCE,),
    )


def test_derives_standard_reaction_enthalpy_with_hess_signs_and_exact_phase() -> None:
    result = derive_standard_reaction_enthalpy(
        _hydrogen_combustion(),
        [
            _formation_enthalpy("species:hydrogen", "g", "0"),
            _formation_enthalpy("species:oxygen", "g", "0"),
            _formation_enthalpy("species:water", "g", "-241.824622"),
            _formation_enthalpy("species:water", "l", "-285.828371"),
        ],
    )

    assert result.status == "complete"
    assert result.value_kj_mol == Decimal("-571.656742")
    assert result.unit == "kJ/mol"
    assert result.classification == "exothermic"
    assert result.reference_temperature_k == Decimal("298.15")
    assert result.standard_pressure_bar == Decimal("1.0")
    assert [item.signed_contribution_kj_mol for item in result.contributions] == [
        Decimal(0),
        Decimal(0),
        Decimal("-571.656742"),
    ]
    assert result.contributions[-1].phase == "l"
    assert result.contributions[-1].sources == [SOURCE]
    assert result.missing_participants == []


def test_reports_unavailable_instead_of_substituting_another_phase() -> None:
    result = derive_standard_reaction_enthalpy(
        _hydrogen_combustion(),
        [
            _formation_enthalpy("species:hydrogen", "g", "0"),
            _formation_enthalpy("species:oxygen", "g", "0"),
            _formation_enthalpy("species:water", "g", "-241.824622"),
        ],
    )

    assert result.status == "unavailable"
    assert result.value_kj_mol is None
    assert result.classification is None
    assert result.reference_temperature_k is None
    assert result.standard_pressure_bar is None
    assert [(item.formula, item.phase, item.reason) for item in result.missing_participants] == [
        ("H2O", "l", "formation_enthalpy_unavailable")
    ]
