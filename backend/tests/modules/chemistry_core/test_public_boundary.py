import ast
import sys
from pathlib import Path

import chem_wiki.modules.chemistry_core as chemistry

EXPECTED_PUBLIC_TYPES = {
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
}


def test_public_api_matches_frozen_m01_scope() -> None:
    assert set(chemistry.__all__) == EXPECTED_PUBLIC_TYPES
    assert all(hasattr(chemistry, name) for name in EXPECTED_PUBLIC_TYPES)


def test_chemistry_core_imports_only_stdlib_or_own_internals() -> None:
    module_root = Path(__file__).parents[3] / "src" / "chem_wiki" / "modules" / "chemistry_core"
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


def test_other_modules_import_chemistry_core_only_from_package_root() -> None:
    package_root = Path(__file__).parents[3] / "src" / "chem_wiki"
    chemistry_core_root = package_root / "modules" / "chemistry_core"
    internal_prefix = "chem_wiki.modules.chemistry_core."
    violations: list[str] = []

    for path in package_root.rglob("*.py"):
        if path.is_relative_to(chemistry_core_root):
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            else:
                continue

            for module in modules:
                if module.startswith(internal_prefix):
                    violations.append(f"{path}:{module}")

    assert violations == []
