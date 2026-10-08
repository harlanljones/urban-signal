"""Validate a national LODES artifact before the daily snapshot consumes it.

The daily snapshot runs in require-national production mode (US-435 §24): it
must never silently publish a metro-only or resolution-incomplete release. The
artifact is built by ``national_builder`` in the separate ``national-publish``
workflow and handed over as a checksum-addressed GitHub Actions artifact, so the
consumer re-checks it independently of the builder that wrote it rather than
trusting the upload:

* the aggregate manifest is present, well-formed, and declares verified
  checksums, a signal source, a LODES vintage, and the required resolutions;
* ``current.json`` names exactly the manifest that is present (no stale or
  mismatched promotion pointer);
* every declared resolution carries a report, at least one data chunk, and at
  least one measured hex with a nonzero total (empty/zeroed builds are refused);
* every chunk listed in a report exists on disk and matches its recorded
  SHA-256, and the manifest's aggregate SHA-256 recomputes over the sorted chunk
  bytes;
* the vintage is not older than the configured age bound.

Any failure exits non-zero so the caller fails closed. On success the resolved
directory is printed for the workflow to pass to ``snapshot_builder
--national-dir``.

Usage::

    python scripts/validate_national_artifact.py --dir build/national
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# The national pyramid the snapshot consumes (national_grid.NATIONAL_RESOLUTIONS,
# duplicated here so this gate has no import-time dependency on polars/httpx).
REQUIRED_RESOLUTIONS: tuple[int, ...] = (4, 5, 6)
# LODES is annual; a monthly build keeps the artifact fresh, so anything older
# than a year-plus slack is a broken/abandoned pipeline, not a real vintage.
DEFAULT_MAX_AGE_DAYS = 400


class NationalArtifactError(ValueError):
    """Raised when the national artifact fails a validation gate."""

    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__(
            "national artifact failed validation: " + "; ".join(failures)
        )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path, failures: list[str], label: str) -> dict | None:
    if not path.exists():
        failures.append(f"{label}: missing {path.name}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        failures.append(f"{label}: unreadable JSON ({exc})")
        return None
    if not isinstance(data, dict):
        failures.append(f"{label}: expected a JSON object")
        return None
    return data


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def validate_national_artifact(
    root: Path,
    *,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    expected_year: int | None = None,
    now: datetime | None = None,
) -> dict:
    """Validate the national tree at ``root`` and return a summary dict.

    ``root`` is the directory that directly contains ``manifest.json``,
    ``current.json`` and the ``res{4,5,6}/`` chunk trees (i.e. the
    ``dist/national`` tree that ``--national-dir``'s parent points at).
    Raises :class:`NationalArtifactError` with every failure found.
    """
    root = Path(root)
    failures: list[str] = []
    now = now or datetime.now(UTC)

    if not root.is_dir():
        raise NationalArtifactError([f"root: {root} is not a directory"])

    manifest = _load_json(root / "manifest.json", failures, "manifest")
    pointer = _load_json(root / "current.json", failures, "current pointer")
    if manifest is None or pointer is None:
        raise NationalArtifactError(failures)

    for field in (
        "generated_at",
        "signal_source",
        "builder_revision",
        "lodes_version",
        "year",
        "resolutions",
        "sha256",
        "checksum_verified",
    ):
        if field not in manifest:
            failures.append(f"manifest: missing '{field}'")

    if manifest.get("checksum_verified") is not True:
        failures.append("manifest: checksum_verified is not true")

    year = manifest.get("year")
    if not isinstance(year, int):
        failures.append(f"manifest: year is not an integer ({year!r})")
    elif expected_year is not None and year != expected_year:
        failures.append(
            f"manifest: year {year} does not match expected {expected_year}"
        )

    generated_at = _parse_iso(str(manifest.get("generated_at", "")))
    if generated_at is None:
        failures.append("manifest: generated_at is not a valid ISO timestamp")
    else:
        age_days = (now - generated_at).total_seconds() / 86400
        if age_days > max_age_days:
            failures.append(
                f"manifest: artifact age {age_days:.1f} days exceeds the "
                f"{max_age_days}-day bound"
            )
        elif age_days < -1:
            failures.append(
                f"manifest: generated_at {generated_at.isoformat()} is in the future"
            )

    declared = manifest.get("resolutions")
    declared_set: set[int] = set()
    if not isinstance(declared, list) or not declared:
        failures.append("manifest: resolutions is missing or empty")
    else:
        for res in declared:
            if not isinstance(res, int):
                failures.append(f"manifest: resolution {res!r} is not an integer")
            else:
                declared_set.add(res)
        missing = sorted(set(REQUIRED_RESOLUTIONS) - declared_set)
        if missing:
            failures.append(f"manifest: missing required resolutions {missing}")

    # Promotion pointer must name exactly the manifest that is present.
    if pointer.get("sha256") != manifest.get("sha256"):
        failures.append(
            "current pointer: sha256 does not match the manifest "
            f"({pointer.get('sha256')!r} != {manifest.get('sha256')!r})"
        )
    if pointer.get("signal_source") != manifest.get("signal_source"):
        failures.append("current pointer: signal_source does not match the manifest")
    if year is not None and pointer.get("year") != year:
        failures.append("current pointer: year does not match the manifest")
    pointer_res = pointer.get("resolutions")
    if isinstance(pointer_res, list) and {
        r for r in pointer_res if isinstance(r, int)
    } != declared_set:
        failures.append("current pointer: resolutions do not match the manifest")

    # Recompute the aggregate SHA-256 over sorted chunk bytes, in declared
    # resolution order — exactly how national_builder._build_manifest built it.
    aggregate = b""
    chunk_count = 0
    rows_measured = 0
    for res in sorted(declared_set):
        res_dir = root / f"res{res}"
        report = _load_json(res_dir / "report.json", failures, f"res{res} report")
        if report is None:
            continue
        if report.get("signal_source") != manifest.get("signal_source"):
            failures.append(f"res{res}: report signal_source does not match manifest")
        if year is not None and report.get("year") != year:
            failures.append(f"res{res}: report year does not match manifest")
        if report.get("resolution") != res:
            failures.append(f"res{res}: report resolution does not match its directory")

        chunks = report.get("chunks")
        if not isinstance(chunks, dict) or not chunks:
            failures.append(f"res{res}: report lists no data chunks")
            continue
        if not (
            (report.get("hexes_with_jobs") or 0) > 0
            or (report.get("hexes_with_workers") or 0) > 0
        ):
            failures.append(f"res{res}: no measured hexes (jobs/workers)")
        if not ((report.get("total_jobs") or 0) > 0 or (report.get("total_workers") or 0) > 0):
            failures.append(f"res{res}: zero aggregate totals")

        recorded = report.get("chunks_sha256")
        if not isinstance(recorded, dict):
            failures.append(f"res{res}: report has no chunks_sha256 map")
            recorded = {}
        for name in sorted(chunks):
            chunk_path = res_dir / name
            if not chunk_path.exists():
                failures.append(f"res{res}: chunk {name} is missing on disk")
                continue
            payload = chunk_path.read_bytes()
            chunk_count += 1
            rows_measured += 1
            digest = _sha256_bytes(payload)
            expected = recorded.get(name)
            if expected is None:
                failures.append(f"res{res}: chunk {name} has no recorded sha256")
            elif digest != expected:
                failures.append(
                    f"res{res}: chunk {name} sha256 mismatch "
                    f"({digest[:12]} != {expected[:12]})"
                )
            aggregate += payload

    if chunk_count == 0:
        failures.append("no readable data chunks in any resolution")

    if failures:
        raise NationalArtifactError(failures)

    aggregate_sha = _sha256_bytes(aggregate)
    if aggregate_sha != manifest.get("sha256"):
        raise NationalArtifactError(
            [
                (
                    "manifest: aggregate sha256 does not match the chunk bytes "
                    f"({aggregate_sha[:12]} != {str(manifest.get('sha256'))[:12]})"
                )
            ]
        )

    return {
        "root": str(root),
        "snapshot_generated_at": generated_at.isoformat() if generated_at else None,
        "signal_source": manifest.get("signal_source"),
        "year": year,
        "builder_revision": manifest.get("builder_revision"),
        "lodes_version": manifest.get("lodes_version"),
        "resolutions": sorted(declared_set),
        "chunks": chunk_count,
        "sha256": manifest.get("sha256"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a national LODES artifact before the daily snapshot consumes it"
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="National root containing manifest.json/current.json/res{4,5,6}",
    )
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument("--expected-year", type=int, default=None)
    args = parser.parse_args(argv)

    try:
        summary = validate_national_artifact(
            Path(args.dir),
            max_age_days=args.max_age_days,
            expected_year=args.expected_year,
        )
    except NationalArtifactError as exc:
        for failure in exc.failures:
            print(f"NATIONAL_ARTIFACT_INVALID: {failure}", file=sys.stderr)
        return 1

    print(
        "NATIONAL_ARTIFACT_OK "
        f"year={summary['year']} resolutions={summary['resolutions']} "
        f"chunks={summary['chunks']} sha256={str(summary['sha256'])[:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
