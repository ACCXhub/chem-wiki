import hashlib
import json
from pathlib import Path

import pytest

from chem_wiki.modules.knowledge_catalog import (
    PINNED_RELEASE,
    ReleaseSourceIdentity,
    ReleaseValidationError,
    verify_release,
)

CONSUMED_ARTIFACTS = {
    "species.jsonl": '{"id":"species:test","entity_kind":"substance"}\n',
    "crosswalk.jsonl": '{"source_id":"source:test"}\n',
    "structure_links.jsonl": '{"source_link_id":"link:test"}\n',
    "reactions.jsonl": '{"id":"reaction:test"}\n',
    "teaching_projection.jsonl": '{"species_id":"species:test"}\n',
    "knowledge_records.jsonl": '{"id":"knowledge:test"}\n',
    "knowledge_links.jsonl": '{"id":"knowledge-link:test"}\n',
    "species_phase_facts.jsonl": '{"id":"phase-fact:test"}\n',
    "species_thermochemistry.jsonl": '{"id":"thermo:test"}\n',
    "phase_transitions.jsonl": '{"id":"phase-transition:test"}\n',
    "bond_enthalpies.jsonl": '{"id":"bond-enthalpy:test"}\n',
}
ARTIFACT_RECORD_COUNTS = {
    "species.jsonl": 309,
    "crosswalk.jsonl": 309,
    "structure_links.jsonl": 69,
    "reactions.jsonl": 183,
    "teaching_projection.jsonl": 309,
    "knowledge_records.jsonl": 637,
    "knowledge_links.jsonl": 176,
    "species_phase_facts.jsonl": 18,
    "species_thermochemistry.jsonl": 20,
    "phase_transitions.jsonl": 2,
    "bond_enthalpies.jsonl": 14,
}


def _write_release(root: Path, *, release: str | None = None, state: str | None = None) -> Path:
    generated = root / "packages" / "consolidated" / "generated"
    generated.mkdir(parents=True)
    files: dict[str, dict[str, object]] = {}
    for name, line in CONSUMED_ARTIFACTS.items():
        content = line * ARTIFACT_RECORD_COUNTS[name]
        artifact = generated / name
        artifact.write_text(content, encoding="utf-8")
        files[name] = {
            "records": ARTIFACT_RECORD_COUNTS[name],
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        }
    manifest = {
        "package": "consolidated",
        "release": release or PINNED_RELEASE.release,
        "state": state or PINNED_RELEASE.state,
        "counts": {
            "species": 309,
            "source_crosswalks": 309,
            "structure_links": 69,
            "reactions": 183,
            "teaching_projections": 309,
            "knowledge_records": 637,
            "knowledge_links": 176,
            "species_phase_facts": 18,
            "species_thermochemistry": 20,
            "phase_transitions": 2,
            "bond_enthalpies": 14,
        },
        "files": files,
    }
    (generated / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return root


def _pinned_identity() -> ReleaseSourceIdentity:
    return ReleaseSourceIdentity(
        repository=PINNED_RELEASE.repository,
        commit=PINNED_RELEASE.commit,
    )


def test_valid_pinned_release_verifies_all_consumed_artifacts(tmp_path: Path) -> None:
    verified = verify_release(_write_release(tmp_path), source_identity=_pinned_identity())

    assert verified.release == "consolidated-1.1.0"
    assert verified.state == "READY_FOR_APP_IMPORT"
    assert tuple(verified.artifacts) == tuple(CONSUMED_ARTIFACTS)


@pytest.mark.parametrize(
    ("release", "state", "expected_code"),
    [
        ("consolidated-0.9.0", None, "release_identity_mismatch"),
        (None, "DRAFT", "release_state_mismatch"),
    ],
)
def test_wrong_release_or_state_is_rejected(
    tmp_path: Path,
    release: str | None,
    state: str | None,
    expected_code: str,
) -> None:
    source = _write_release(tmp_path, release=release, state=state)

    with pytest.raises(ReleaseValidationError) as error:
        verify_release(source, source_identity=_pinned_identity())

    assert error.value.code == expected_code


def test_modified_consumed_artifact_hash_is_rejected(tmp_path: Path) -> None:
    source = _write_release(tmp_path)
    artifact = source / "packages" / "consolidated" / "generated" / "species.jsonl"
    artifact.write_text(artifact.read_text(encoding="utf-8") + "tampered", encoding="utf-8")

    with pytest.raises(ReleaseValidationError) as error:
        verify_release(source, source_identity=_pinned_identity())

    assert error.value.code == "artifact_hash_mismatch"
    assert error.value.artifact == "species.jsonl"


def test_line_ending_rewrite_is_rejected_by_byte_exact_hash(tmp_path: Path) -> None:
    source = _write_release(tmp_path)
    artifact = source / "packages" / "consolidated" / "generated" / "species.jsonl"
    artifact.write_bytes(artifact.read_bytes().replace(b"\n", b"\r\n"))

    with pytest.raises(ReleaseValidationError) as error:
        verify_release(source, source_identity=_pinned_identity())

    assert error.value.code == "artifact_hash_mismatch"
    assert error.value.artifact == "species.jsonl"


def test_wrong_repository_or_commit_is_rejected(tmp_path: Path) -> None:
    source = _write_release(tmp_path)

    with pytest.raises(ReleaseValidationError) as error:
        verify_release(
            source,
            source_identity=ReleaseSourceIdentity(
                repository="https://example.invalid/other.git",
                commit="0" * 40,
            ),
        )

    assert error.value.code == "source_identity_mismatch"
