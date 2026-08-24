"""RDKit adapter for the library-neutral M06 chemistry engine port."""

from uuid import uuid4

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

from chem_wiki.modules.chemistry_core import StructureId

from .application import (
    AtomCoordinate,
    DetectedFunctionalGroup,
    FunctionalGroupOccurrence,
    StructureAnalysis,
    StructureConformer,
    StructureDepiction,
    StructureDescriptors,
    StructureInput,
)
from .catalog import FUNCTIONAL_GROUP_PATTERNS

DEPICTION_WIDTH = 600
DEPICTION_HEIGHT = 420
SUPPORTED_FORMATS = frozenset({"smiles", "molblock"})


def _parse(structure: StructureInput) -> Chem.Mol | None:
    text = structure.text.strip()
    if not text:
        return None
    if structure.format == "smiles":
        return Chem.MolFromSmiles(text)
    return Chem.MolFromMolBlock(text, sanitize=True, removeHs=False, strictParsing=True)


def _depict(molecule: Chem.Mol) -> StructureDepiction:
    molecule_2d = Chem.Mol(molecule)
    rdDepictor.Compute2DCoords(molecule_2d)
    drawer = rdMolDraw2D.MolDraw2DSVG(DEPICTION_WIDTH, DEPICTION_HEIGHT)
    drawer.DrawMolecule(molecule_2d)
    coordinates = tuple(
        AtomCoordinate(atom_index=index, x=round(point.x, 3), y=round(point.y, 3))
        for index in range(molecule_2d.GetNumAtoms())
        for point in (drawer.GetDrawCoords(index),)
    )
    drawer.FinishDrawing()
    return StructureDepiction(
        svg=drawer.GetDrawingText(),
        width=DEPICTION_WIDTH,
        height=DEPICTION_HEIGHT,
        atom_coordinates=coordinates,
    )


def _conformer(molecule: Chem.Mol) -> StructureConformer:
    molecule_3d = Chem.AddHs(Chem.Mol(molecule))
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = 0xC0DE
    if AllChem.EmbedMolecule(molecule_3d, parameters) != 0:
        return StructureConformer(
            state="unavailable",
            reason="当前结构无法生成可靠的三维构象",
        )
    if AllChem.MMFFHasAllMoleculeParams(molecule_3d):
        AllChem.MMFFOptimizeMolecule(molecule_3d, maxIters=200)
    elif AllChem.UFFHasAllMoleculeParams(molecule_3d):
        AllChem.UFFOptimizeMolecule(molecule_3d, maxIters=200)
    return StructureConformer(state="available", mol_block=Chem.MolToMolBlock(molecule_3d))


def _functional_groups(molecule: Chem.Mol) -> tuple[DetectedFunctionalGroup, ...]:
    detected: list[DetectedFunctionalGroup] = []
    for definition in FUNCTIONAL_GROUP_PATTERNS:
        query = Chem.MolFromSmarts(definition.smarts)
        if query is None:
            raise RuntimeError(f"invalid M06 SMARTS catalog entry: {definition.key}")
        matches = molecule.GetSubstructMatches(query, uniquify=True)
        if not matches:
            continue
        detected.append(
            DetectedFunctionalGroup(
                functional_group_id=definition.entity.id,
                key=definition.key,
                name_zh=definition.name_zh,
                name_en=definition.name_en,
                smarts=definition.smarts,
                pattern_source=definition.pattern_source,
                occurrences=tuple(
                    FunctionalGroupOccurrence(atom_indices=tuple(match)) for match in matches
                ),
            )
        )
    return tuple(detected)


class RdkitChemistryEngine:
    """Translate RDKit results into stable M06 DTO values."""

    def analyze(self, structure: StructureInput) -> StructureAnalysis:
        if structure.format not in SUPPORTED_FORMATS:
            return StructureAnalysis(
                state="unsupported",
                input_format=structure.format,
                code="unsupported_format",
                message="当前仅支持 SMILES 与 molfile 结构输入",
            )
        molecule = _parse(structure)
        if molecule is None:
            return StructureAnalysis(
                state="invalid",
                input_format=structure.format,
                code="invalid_structure",
                message="无法解析该结构，或原子价态不合法",
            )

        return StructureAnalysis(
            state="valid",
            input_format=structure.format,
            structure_id=StructureId(uuid4()),
            canonical_smiles=Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True),
            formula=rdMolDescriptors.CalcMolFormula(molecule),
            descriptors=StructureDescriptors(
                molecular_weight=round(Descriptors.MolWt(molecule), 3),
                exact_mass=round(Descriptors.ExactMolWt(molecule), 4),
                heavy_atom_count=Descriptors.HeavyAtomCount(molecule),
                hydrogen_bond_donors=Descriptors.NumHDonors(molecule),
                hydrogen_bond_acceptors=Descriptors.NumHAcceptors(molecule),
                rotatable_bond_count=Descriptors.NumRotatableBonds(molecule),
                formal_charge=Chem.GetFormalCharge(molecule),
            ),
            depiction=_depict(molecule),
            conformer=_conformer(molecule),
            functional_groups=_functional_groups(molecule),
        )
