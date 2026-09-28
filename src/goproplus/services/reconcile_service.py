"""Reconcile use-case: link files already on disk to catalog rows.

For a fresh catalog (e.g. after a DB reset) this scans the download tree,
matches files to known items by filename, files them into the canonical
layout, and marks them downloaded — avoiding a full re-download.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

from goproplus.domain.media import MediaFilter
from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.database.schema import ItemStatus
from goproplus.infra.storage import layout_path


@dataclass(slots=True)
class ReconcileResult:
    matched: int = 0
    unmatched_files: list[str] = field(default_factory=list)
    moved: int = 0


def run_reconcile(
    repository: MediaRepository,
    dest_dir: Path,
    *,
    apply: bool = True,
    log: Optional[Callable[[str], None]] = None,
) -> ReconcileResult:
    """Match on-disk files to catalog items by filename.

    Only items not yet downloaded (status KNOWN) participate; already
    downloaded rows are left alone. When a matched file is not at its
    canonical path it is moved there first.
    """
    log = log or (lambda message: None)
    result = ReconcileResult()
    dest_dir = Path(dest_dir)

    disk_files = {
        path.name: path
        for path in sorted(dest_dir.rglob("*"))
        if path.is_file()
    }

    candidates = repository.find(MediaFilter(), status=ItemStatus.KNOWN)
    taken: set[str] = set()
    for item in candidates:
        disk_path = disk_files.get(item.filename)
        if disk_path is None or item.filename in taken:
            continue
        taken.add(item.filename)
        result.matched += 1
        expected = layout_path(dest_dir, item.filename, item.captured_at, item.media_type)
        if apply:
            if disk_path != expected:
                expected.parent.mkdir(parents=True, exist_ok=True)
                disk_path.rename(expected)
                result.moved += 1
            repository.mark_downloaded(item.id, str(expected))
        else:
            if disk_path != expected:
                result.moved += 1

    result.unmatched_files = sorted(name for name in disk_files if name not in taken)
    return result
