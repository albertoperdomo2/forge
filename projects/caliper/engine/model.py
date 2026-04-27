"""Types shared by the file export pipeline (artifact uploads)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FileExportManifest:
    """Files to upload to external backends."""

    source_paths: list[Path]
    run_identity: dict[str, Any]
    backends_enabled: frozenset[str]


@dataclass
class FileExportBackendResult:
    """Per-backend export outcome."""

    backend: str
    status: str  # success | failure | skipped
    detail: str = ""
    metadata: dict[str, Any] | None = field(default=None)
