"""Interlock gap metric (Agent Interlock design doc, section 6).

Compares the share of changed FILES that are spine against the share of
changed LINES that are spine, for a git diff range. A wide gap — many spine
files, few spine lines — is the signature of work that parallelizes cleanly
with a serialized tail. A high share on both means the streams were never
independent.

Usage:
    python scripts/interlock_gap.py [BASE]
Defaults BASE to the merge-base with origin/main when it exists, else HEAD~1.
"""

import subprocess
import sys
from dataclasses import dataclass

DEFAULT_MANIFEST = "docs/agents/spine-manifest.txt"


@dataclass
class InterlockGap:
    spine_files: int
    leaf_files: int
    spine_lines: int
    leaf_lines: int

    @property
    def total_files(self) -> int:
        return self.spine_files + self.leaf_files

    @property
    def total_lines(self) -> int:
        return self.spine_lines + self.leaf_lines

    @property
    def file_share(self) -> float:
        return self.spine_files / self.total_files if self.total_files else 0.0

    @property
    def line_share(self) -> float:
        return self.spine_lines / self.total_lines if self.total_lines else 0.0

    @property
    def reading(self) -> str:
        if not self.total_files:
            return "no changes in range"
        high_file, low_line = self.file_share >= 0.5, self.line_share <= 0.3
        if high_file and low_line:
            return (
                "wide gap: few small spine edits carry the risk — "
                "parallelize leaves, serialize the interlock"
            )
        if high_file and not low_line:
            return "high spine share on both axes: streams are not independent; merge them"
        return (
            f"most delivered work is leaf; keep the interlock scoped to "
            f"{self.spine_files} small spine edits carrying {self.line_share:.0%} of lines"
        )


def compute_gap(numstat_rows: list[tuple[int, int, str]], spine_paths: set[str]) -> InterlockGap:
    gap = InterlockGap(spine_files=0, leaf_files=0, spine_lines=0, leaf_lines=0)
    for _added, _deleted, path in numstat_rows:
        added = max(_added, 1)  # binary or empty diffs still count as a touched line
        if path in spine_paths:
            gap.spine_files += 1
            gap.spine_lines += added
        else:
            gap.leaf_files += 1
            gap.leaf_lines += added
    return gap


def load_manifest(manifest_path: str) -> set[str]:
    paths = set()
    with open(manifest_path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                paths.add(stripped)
    return paths


def numstat(base: str, head: str = "HEAD") -> list[tuple[int, int, str]]:
    out = subprocess.run(
        ["git", "diff", "--numstat", f"{base}..{head}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        rows.append((int(added) if added.isdigit() else 0, int(deleted) if deleted.isdigit() else 0, path))
    return rows


def default_base() -> str:
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", "origin/main"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "origin/main" if merge_base.returncode == 0 else "HEAD~1"


def main(argv: list[str]) -> int:
    base = argv[1] if len(argv) > 1 else default_base()
    spine = load_manifest(DEFAULT_MANIFEST)
    gap = compute_gap(numstat(base), spine)
    print(f"range: {base}..HEAD")
    print(f"files  spine {gap.spine_files:>3} / {gap.total_files:<3} share {gap.file_share:.2f}")
    print(f"lines  spine {gap.spine_lines:>3} / {gap.total_lines:<3} share {gap.line_share:.2f}")
    print(f"reading: {gap.reading}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
