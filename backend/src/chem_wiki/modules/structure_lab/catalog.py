"""Stable M06 FunctionalGroup catalog and RDKit SMARTS inputs."""

from dataclasses import dataclass
from uuid import UUID

from chem_wiki.modules.chemistry_core import FunctionalGroup, FunctionalGroupId


@dataclass(frozen=True, slots=True)
class FunctionalGroupPattern:
    entity: FunctionalGroup
    key: str
    name_zh: str
    name_en: str
    smarts: str
    pattern_source: str


RDKIT_HIERARCHY_SOURCE = "RDKit Functional_Group_Hierarchy.txt"
RDKIT_FRAGMENT_SOURCE = "RDKit FragmentDescriptors.csv"


def _pattern(
    identifier: str,
    key: str,
    name_zh: str,
    name_en: str,
    smarts: str,
    source: str,
) -> FunctionalGroupPattern:
    return FunctionalGroupPattern(
        entity=FunctionalGroup(FunctionalGroupId(UUID(identifier)), name_en),
        key=key,
        name_zh=name_zh,
        name_en=name_en,
        smarts=smarts,
        pattern_source=source,
    )


# IDs and keys are M06-owned stable catalog identity. SMARTS values are consumed only by
# the RDKit adapter and are based on RDKit's bundled functional-group/fragment definitions.
FUNCTIONAL_GROUP_PATTERNS: tuple[FunctionalGroupPattern, ...] = (
    _pattern(
        "206a72f6-1c27-54c7-a74b-9907511a59dd",
        "alcohol",
        "醇羟基",
        "alcohol",
        "[O;H1;$(O-!@[C;!$(C=!@[O,N,S])])]",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "e7fefb97-6dbe-5eed-98ec-57513ae4698a",
        "phenol",
        "酚羟基",
        "phenol",
        "[O;H1;$(O-!@c)]",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "9241010d-dd59-519b-a4af-558873d70641",
        "aldehyde",
        "醛基",
        "aldehyde",
        "[CH;D2;!$(C-[!#6;!#1])]=O",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "5b092c00-c7fe-5517-a988-d4e872e29e77",
        "ketone",
        "酮羰基",
        "ketone",
        "[#6][CX3](=O)[#6]",
        RDKIT_FRAGMENT_SOURCE,
    ),
    _pattern(
        "20cd8d76-5c24-5eb2-a38c-3092b3c86744",
        "carboxylic_acid",
        "羧基",
        "carboxylic acid",
        "C(=O)[O;H,-]",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "682053e9-45d4-52d3-823f-983ec01dc5d9",
        "ester",
        "酯基",
        "ester",
        "[#6][CX3](=O)[OX2H0][#6]",
        RDKIT_FRAGMENT_SOURCE,
    ),
    _pattern(
        "7c6b07da-8395-5f98-bf31-aa84b1721196",
        "ether",
        "醚键",
        "ether",
        "[OD2;!$(O-C=O)]([#6])[#6]",
        RDKIT_FRAGMENT_SOURCE,
    ),
    _pattern(
        "d566e9fe-72c6-5893-bcb8-41464445e50a",
        "amine",
        "氨基",
        "amine",
        "[N;$(N-[#6]);!$(N-[!#6;!#1]);!$(N-C=[O,N,S])]",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "457b7e89-4685-538a-91bf-de8577bc445a",
        "amide",
        "酰胺基",
        "amide",
        "C(=O)-N",
        RDKIT_FRAGMENT_SOURCE,
    ),
    _pattern(
        "0abafb1a-5b70-5b1d-9099-d15a30bd2713",
        "nitrile",
        "氰基",
        "nitrile",
        "[NX1]#[CX2]",
        RDKIT_FRAGMENT_SOURCE,
    ),
    _pattern(
        "09e66954-61c3-5024-b02c-6edeed6806e4",
        "haloalkane",
        "卤素原子",
        "organic halogen",
        "[$([F,Cl,Br,I]-!@[#6]);!$([F,Cl,Br,I]-[C,S](=[O,S,N]))]",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "686758cd-88c0-5450-8a10-1ae8222696c1",
        "nitro",
        "硝基",
        "nitro",
        "[N;H0;$(N-[#6]);D3](=[O;D1])~[O;D1]",
        RDKIT_HIERARCHY_SOURCE,
    ),
    _pattern(
        "8560a573-6392-5db3-a1b8-dfd373e21228",
        "alkene",
        "碳碳双键",
        "alkene",
        "[C;!$(C=O)]=[C;!$(C=O)]",
        "M06 curriculum SMARTS evaluated by RDKit",
    ),
    _pattern(
        "ffdfff1b-6c1f-5ef0-989d-58b2e6103fa9",
        "alkyne",
        "碳碳三键",
        "alkyne",
        "[C]#[C]",
        "M06 curriculum SMARTS evaluated by RDKit",
    ),
)
