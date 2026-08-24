"""Source-neutral M03 periodic-table read model."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ElementCategory = Literal[
    "alkali-metal",
    "alkaline-earth-metal",
    "transition-metal",
    "post-transition-metal",
    "metalloid",
    "reactive-nonmetal",
    "halogen",
    "noble-gas",
    "lanthanide",
    "actinide",
]


class IncompletePeriodicTableError(ValueError):
    """Raised when PostgreSQL does not contain the complete canonical range."""


@dataclass(frozen=True, slots=True)
class CanonicalElementSnapshot:
    id: UUID
    atomic_number: int
    symbol: str
    name_zh: str
    name_en: str
    electronegativity: float | None
    electronegativity_scale: str | None
    first_ionization_energy: float | None
    first_ionization_energy_unit: str | None


class PeriodicTableLayout(BaseModel):
    period: int
    group: int | None
    row: int
    column: int
    block: Literal["s", "p", "d", "f"]


class ScalarProperty(BaseModel):
    value: float | None
    unit: str | None


class PeriodicTableProperties(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    electronegativity: ScalarProperty
    first_ionization_energy: ScalarProperty = Field(alias="firstIonizationEnergy")


class PeriodicTableElement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    atomic_number: int = Field(alias="atomicNumber")
    symbol: str
    name_zh: str = Field(alias="nameZh")
    name_en: str = Field(alias="nameEn")
    category: ElementCategory
    status: Literal["confirmed", "predicted"]
    layout: PeriodicTableLayout
    properties: PeriodicTableProperties


_NOBLE_GASES = frozenset({2, 10, 18, 36, 54, 86, 118})
_HALOGENS = frozenset({9, 17, 35, 53, 85, 117})
_REACTIVE_NONMETALS = frozenset({1, 6, 7, 8, 15, 16, 34})
_METALLOIDS = frozenset({5, 14, 32, 33, 51, 52})
_POST_TRANSITION_METALS = frozenset({13, 31, 49, 50, 81, 82, 83, 84, 113, 114, 115, 116})
_ALKALI_METALS = frozenset({3, 11, 19, 37, 55, 87})
_ALKALINE_EARTH_METALS = frozenset({4, 12, 20, 38, 56, 88})


def validate_canonical_range(atomic_numbers: object) -> None:
    if list(atomic_numbers) != list(range(1, 119)):
        raise IncompletePeriodicTableError(
            "canonical periodic table requires each atomic number from 1 through 118"
        )


def _layout_for(atomic_number: int) -> PeriodicTableLayout:
    if 57 <= atomic_number <= 71:
        return PeriodicTableLayout(
            period=6,
            group=None,
            row=8,
            column=atomic_number - 54,
            block="f",
        )
    if 89 <= atomic_number <= 103:
        return PeriodicTableLayout(
            period=7,
            group=None,
            row=9,
            column=atomic_number - 86,
            block="f",
        )

    if atomic_number == 1:
        period, group = 1, 1
    elif atomic_number == 2:
        period, group = 1, 18
    elif 3 <= atomic_number <= 4:
        period, group = 2, atomic_number - 2
    elif 5 <= atomic_number <= 10:
        period, group = 2, atomic_number + 8
    elif 11 <= atomic_number <= 12:
        period, group = 3, atomic_number - 10
    elif 13 <= atomic_number <= 18:
        period, group = 3, atomic_number
    elif 19 <= atomic_number <= 36:
        period, group = 4, atomic_number - 18
    elif 37 <= atomic_number <= 54:
        period, group = 5, atomic_number - 36
    elif 55 <= atomic_number <= 56:
        period, group = 6, atomic_number - 54
    elif 72 <= atomic_number <= 86:
        period, group = 6, atomic_number - 68
    elif 87 <= atomic_number <= 88:
        period, group = 7, atomic_number - 86
    elif 104 <= atomic_number <= 118:
        period, group = 7, atomic_number - 100
    else:  # pragma: no cover - guarded by M02 and validate_canonical_range
        raise ValueError(f"unsupported atomic number: {atomic_number}")

    if atomic_number == 2 or group <= 2:
        block: Literal["s", "p", "d", "f"] = "s"
    elif group >= 13:
        block = "p"
    else:
        block = "d"
    return PeriodicTableLayout(
        period=period,
        group=group,
        row=period,
        column=group,
        block=block,
    )


def _category_for(atomic_number: int) -> ElementCategory:
    if 57 <= atomic_number <= 71:
        return "lanthanide"
    if 89 <= atomic_number <= 103:
        return "actinide"
    if atomic_number in _NOBLE_GASES:
        return "noble-gas"
    if atomic_number in _HALOGENS:
        return "halogen"
    if atomic_number in _REACTIVE_NONMETALS:
        return "reactive-nonmetal"
    if atomic_number in _METALLOIDS:
        return "metalloid"
    if atomic_number in _POST_TRANSITION_METALS:
        return "post-transition-metal"
    if atomic_number in _ALKALI_METALS:
        return "alkali-metal"
    if atomic_number in _ALKALINE_EARTH_METALS:
        return "alkaline-earth-metal"
    return "transition-metal"


def build_periodic_table(
    snapshots: list[CanonicalElementSnapshot] | tuple[CanonicalElementSnapshot, ...],
) -> list[PeriodicTableElement]:
    elements: list[PeriodicTableElement] = []
    for snapshot in sorted(snapshots, key=lambda item: item.atomic_number):
        elements.append(
            PeriodicTableElement(
                id=snapshot.id,
                atomicNumber=snapshot.atomic_number,
                symbol=snapshot.symbol,
                nameZh=snapshot.name_zh,
                nameEn=snapshot.name_en,
                category=_category_for(snapshot.atomic_number),
                status="confirmed",
                layout=_layout_for(snapshot.atomic_number),
                properties=PeriodicTableProperties(
                    electronegativity=ScalarProperty(
                        value=snapshot.electronegativity,
                        unit=snapshot.electronegativity_scale,
                    ),
                    firstIonizationEnergy=ScalarProperty(
                        value=snapshot.first_ionization_energy,
                        unit=snapshot.first_ionization_energy_unit,
                    ),
                ),
            )
        )
    return elements
