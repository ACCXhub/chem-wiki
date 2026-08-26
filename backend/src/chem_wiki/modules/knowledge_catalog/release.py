"""Pinned consolidated release identity and artifact verification."""

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONSUMED_ARTIFACTS = (
    "species.jsonl",
    "crosswalk.jsonl",
    "structure_links.jsonl",
    "reactions.jsonl",
    "teaching_projection.jsonl",
)


@dataclass(frozen=True, slots=True)
class PinnedRelease:
    repository: str
    release: str
    commit: str
    state: str
    expected_counts: tuple[tuple[str, int], ...]


PINNED_RELEASE = PinnedRelease(
    repository="https://github.com/ACCXhub/chem-knowledge-data.git",
    release="consolidated-1.0.0",
    commit="c1bf05dd68c936cb0cedf8c6877bbac0f68025e9",
    state="READY_FOR_APP_IMPORT",
    expected_counts=(
        ("species", 309),
        ("source_crosswalks", 309),
        ("structure_links", 69),
        ("reactions", 183),
        ("teaching_projections", 309),
    ),
)


@dataclass(frozen=True, slots=True)
class ReleaseSourceIdentity:
    repository: str
    commit: str


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    name: str
    path: Path
    sha256: str
    records: int


@dataclass(frozen=True, slots=True)
class VerifiedRelease:
    source_root: Path
    manifest_path: Path
    manifest_sha256: str
    release: str
    state: str
    artifacts: dict[str, VerifiedArtifact]
    manifest: dict[str, Any]


class ReleaseValidationError(ValueError):
    def __init__(self, code: str, message: str, *, artifact: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.artifact = artifact


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_repository(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized.removesuffix(".git").casefold()


def _run_git(source_root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(source_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReleaseValidationError(
            "source_identity_unavailable",
            f"无法读取 consolidated release Git identity：{error}",
        ) from error
    return completed.stdout.strip()


def read_git_source_identity(source_root: Path) -> ReleaseSourceIdentity:
    return ReleaseSourceIdentity(
        repository=_run_git(source_root, "remote", "get-url", "origin"),
        commit=_run_git(source_root, "rev-parse", "HEAD"),
    )


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReleaseValidationError(
            "manifest_missing", f"缺少 consolidated manifest：{path}", artifact="manifest.json"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseValidationError(
            "manifest_invalid", f"无法读取 consolidated manifest：{error}", artifact="manifest.json"
        ) from error
    if not isinstance(payload, dict):
        raise ReleaseValidationError(
            "manifest_invalid", "consolidated manifest 必须是 JSON object", artifact="manifest.json"
        )
    return payload


def verify_release(
    source_root: Path,
    *,
    source_identity: ReleaseSourceIdentity | None = None,
) -> VerifiedRelease:
    """Verify the pinned Git source, manifest identity, counts and consumed artifacts."""

    root = source_root.resolve()
    identity = source_identity or read_git_source_identity(root)
    if (
        _normalize_repository(identity.repository)
        != _normalize_repository(PINNED_RELEASE.repository)
        or identity.commit.casefold() != PINNED_RELEASE.commit
    ):
        raise ReleaseValidationError(
            "source_identity_mismatch",
            "本地 consolidated source 与 pinned repository/commit 不一致",
        )

    manifest_path = root / "packages" / "consolidated" / "generated" / "manifest.json"
    manifest = _load_manifest(manifest_path)
    if manifest.get("package") != "consolidated" or manifest.get("release") != (
        PINNED_RELEASE.release
    ):
        raise ReleaseValidationError(
            "release_identity_mismatch", "consolidated release identity 与应用 pin 不一致"
        )
    if manifest.get("state") != PINNED_RELEASE.state:
        raise ReleaseValidationError(
            "release_state_mismatch", "consolidated release state 未达到 READY_FOR_APP_IMPORT"
        )

    counts = manifest.get("counts")
    if not isinstance(counts, dict) or any(
        counts.get(name) != expected for name, expected in PINNED_RELEASE.expected_counts
    ):
        raise ReleaseValidationError(
            "release_count_mismatch", "consolidated manifest counts 与 pinned release 不一致"
        )

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ReleaseValidationError("manifest_invalid", "manifest.files 必须是 JSON object")

    generated_root = manifest_path.parent
    artifacts: dict[str, VerifiedArtifact] = {}
    expected_by_artifact = {
        "species.jsonl": dict(PINNED_RELEASE.expected_counts)["species"],
        "crosswalk.jsonl": dict(PINNED_RELEASE.expected_counts)["source_crosswalks"],
        "structure_links.jsonl": dict(PINNED_RELEASE.expected_counts)["structure_links"],
        "reactions.jsonl": dict(PINNED_RELEASE.expected_counts)["reactions"],
        "teaching_projection.jsonl": dict(PINNED_RELEASE.expected_counts)["teaching_projections"],
    }
    for name in CONSUMED_ARTIFACTS:
        metadata = files.get(name)
        path = generated_root / name
        if not isinstance(metadata, dict) or not path.is_file():
            raise ReleaseValidationError(
                "artifact_missing", f"缺少 consumed artifact：{name}", artifact=name
            )
        expected_sha256 = metadata.get("sha256")
        actual_sha256 = _sha256(path)
        if not isinstance(expected_sha256, str) or actual_sha256 != expected_sha256:
            raise ReleaseValidationError(
                "artifact_hash_mismatch", f"artifact SHA-256 不匹配：{name}", artifact=name
            )
        actual_records = sum(
            1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        )
        if (
            metadata.get("records") != actual_records
            or actual_records != expected_by_artifact[name]
        ):
            raise ReleaseValidationError(
                "artifact_count_mismatch", f"artifact record count 不匹配：{name}", artifact=name
            )
        artifacts[name] = VerifiedArtifact(
            name=name,
            path=path,
            sha256=actual_sha256,
            records=actual_records,
        )

    return VerifiedRelease(
        source_root=root,
        manifest_path=manifest_path,
        manifest_sha256=_sha256(manifest_path),
        release=PINNED_RELEASE.release,
        state=PINNED_RELEASE.state,
        artifacts=artifacts,
        manifest=manifest,
    )
