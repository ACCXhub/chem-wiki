from datetime import UTC, datetime
from importlib import import_module
from typing import Any


def _load_sources() -> tuple[Any, Any, Any]:
    return (
        import_module("chem_wiki.modules.element_data.iupac"),
        import_module("chem_wiki.modules.element_data.periodic_table_pro"),
        import_module("chem_wiki.modules.element_data.official_chinese_names"),
    )


def test_identity_source_loaders_cover_exactly_118_complete_unique_elements() -> None:
    iupac, periodic_table_pro, official_chinese_names = _load_sources()

    iupac_records = iupac.load_iupac_elements()
    seed_records = periodic_table_pro.load_periodic_table_pro_names()
    supplement_records = official_chinese_names.load_official_chinese_names()

    assert [record.atomic_number for record in iupac_records] == list(range(1, 119))
    assert len({record.symbol for record in iupac_records}) == 118
    assert len({record.name_en for record in iupac_records}) == 118
    assert (iupac_records[0].symbol, iupac_records[0].name_en) == ("H", "hydrogen")
    assert (iupac_records[-1].symbol, iupac_records[-1].name_en) == ("Og", "oganesson")

    assert len(seed_records) == 116
    assert {record.atomic_number for record in seed_records} == set(range(1, 117))
    assert len({record.name_zh for record in seed_records}) == 116
    assert all(record.atomic_number not in {117, 118} for record in seed_records)

    assert [(record.atomic_number, record.name_zh) for record in supplement_records] == [
        (117, "鿬"),
        (118, "鿫"),
    ]
    assert len({record.name_zh for record in (*seed_records, *supplement_records)}) == 118


def test_each_identity_record_carries_auditable_source_evidence() -> None:
    iupac, periodic_table_pro, official_chinese_names = _load_sources()
    source_sets = (
        iupac.load_iupac_elements(),
        periodic_table_pro.load_periodic_table_pro_names(),
        official_chinese_names.load_official_chinese_names(),
    )

    assert {
        source_sets[0][0].source_key,
        source_sets[1][0].source_key,
        source_sets[2][0].source_key,
    } == {
        "iupac-periodic-table-2022",
        "periodic-table-pro-zhcn",
        "cnctst-official-element-names-2017",
    }
    assert source_sets[1][0].source_key != source_sets[2][0].source_key

    for records in source_sets:
        for record in records:
            assert record.source_url.startswith(("http://", "https://"))
            assert record.retrieved_at == datetime(2026, 8, 20, tzinfo=UTC)
            assert len(record.content_sha256) == 64
            assert set(record.content_sha256) <= set("0123456789abcdef")
            assert record.raw_value
