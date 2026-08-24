from importlib import import_module
from uuid import UUID


def _module():
    return import_module("chem_wiki.modules.periodic_table.read_model")


def _snapshot(atomic_number: int, **overrides: object):
    read_model = _module()
    values: dict[str, object] = {
        "id": UUID(int=atomic_number),
        "atomic_number": atomic_number,
        "symbol": f"E{atomic_number}",
        "name_zh": f"元素{atomic_number}",
        "name_en": f"element-{atomic_number}",
        "electronegativity": None,
        "electronegativity_scale": None,
        "first_ionization_energy": None,
        "first_ionization_energy_unit": None,
    }
    values.update(overrides)
    return read_model.CanonicalElementSnapshot(**values)


def test_build_read_model_sorts_elements_and_assigns_canonical_layout() -> None:
    read_model = _module()

    elements = read_model.build_periodic_table(
        [
            _snapshot(118, symbol="Og", name_zh="鿫", name_en="oganesson"),
            _snapshot(
                1,
                symbol="H",
                name_zh="氢",
                name_en="hydrogen",
                electronegativity=2.2,
                electronegativity_scale="Pauling",
                first_ionization_energy=13.598,
                first_ionization_energy_unit="eV",
            ),
            _snapshot(58, symbol="Ce", name_zh="铈", name_en="cerium"),
        ]
    )

    assert [element.atomic_number for element in elements] == [1, 58, 118]
    assert elements[0].layout.model_dump() == {
        "period": 1,
        "group": 1,
        "row": 1,
        "column": 1,
        "block": "s",
    }
    assert elements[1].layout.model_dump() == {
        "period": 6,
        "group": None,
        "row": 8,
        "column": 4,
        "block": "f",
    }
    assert elements[2].layout.model_dump() == {
        "period": 7,
        "group": 18,
        "row": 7,
        "column": 18,
        "block": "p",
    }
    assert elements[0].category == "reactive-nonmetal"
    assert elements[1].category == "lanthanide"
    assert elements[2].category == "noble-gas"


def test_build_read_model_exposes_source_neutral_properties_and_explicit_missing_values() -> None:
    read_model = _module()

    hydrogen, helium = read_model.build_periodic_table(
        [
            _snapshot(
                1,
                symbol="H",
                electronegativity=2.2,
                electronegativity_scale="Pauling",
                first_ionization_energy=13.598,
                first_ionization_energy_unit="eV",
            ),
            _snapshot(2, symbol="He"),
        ]
    )

    assert hydrogen.properties.model_dump(by_alias=True) == {
        "electronegativity": {"value": 2.2, "unit": "Pauling"},
        "firstIonizationEnergy": {"value": 13.598, "unit": "eV"},
    }
    assert helium.properties.model_dump(by_alias=True) == {
        "electronegativity": {"value": None, "unit": None},
        "firstIonizationEnergy": {"value": None, "unit": None},
    }
    assert hydrogen.status == "confirmed"
    assert "source" not in hydrogen.model_dump_json()
    assert "claim" not in hydrogen.model_dump_json()


def test_validate_canonical_range_rejects_partial_or_duplicate_data() -> None:
    read_model = _module()

    try:
        read_model.validate_canonical_range([1, 2, 2, 4])
    except read_model.IncompletePeriodicTableError as exc:
        assert str(exc) == "canonical periodic table requires each atomic number from 1 through 118"
    else:
        raise AssertionError("partial canonical data must be rejected")

    read_model.validate_canonical_range(range(1, 119))
