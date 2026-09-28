"""Organize use-case: re-file downloaded items to match the current layout.

Runs entirely offline (DB + filesystem, no network). Reusable whenever the
destination layout changes: it computes the canonical path for every
downloaded item and moves files that are not in their canonical spot.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from goproplus.domain.media import MediaType
from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.storage import layout_path


@dataclass(slots=True)
class OrganizeResult:
    checked: int = 0
    moved: list[tuple[str, str]] = field(default_factory=list)  # (from, to)
    unchanged: int = 0
    missing_on_disk: int = 0
    collisions: int = 0


def run_organize(
    repository,
    dest_dir: Path,
    *,
    apply: bool = True,
    log=None,
) -> OrganizeResult:
    """Move downloaded files into the canonical layout and update the DB.

    With apply=False, only report what would change (dry run).
    """
    log = log or (lambda message: None)
    result = OrganizeResult()
    dest_dir = Path(dest_dir)

    for record in repository.find_downloaded():
        result.checked += 1
        if not record.local_path:
            result.missing_on_disk += 1
            continue

        current = Path(record.local_path)
        expected = layout_path(dest_dir, record.filename, record.captured_at, MediaType(record.media_type))
        if current == expected:
            result.unchanged += 1
            continue

        if not current.exists():
            result.missing_on_disk += 1
            log(f"not on disk (leaving as-is): {current}")
            continue
        if expected.exists():
            result.collisions += 1
            log(f"target already exists, skipping: {expected}")
            continue

        if apply:
            expected.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(expected))
            repository.update_local_path(record.id, str(expected))
        result.moved.append((str(current), str(expected)))

    if apply:
        log(
            f"organized {result.checked} downloaded items: {len(result.moved)} moved, "
            f"{result.unchanged} already in place, {result.missing_on_disk} missing on disk, "
            f"{result.collisions} skipped (target exists)."
        )
    return result
