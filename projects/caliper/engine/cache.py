"""Parse cache read/write with input fingerprint (FR-016)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

CACHE_SCHEMA_VERSION = "1"


def fingerprint_base_dir(base_dir: Path, plugin_module: str) -> str:
    """Stable hash over file paths + mtimes under base_dir."""
    base_dir = base_dir.resolve()
    entries: list[tuple[str, int, int]] = []
    for root, _dirs, files in os.walk(base_dir):
        for name in sorted(files):
            p = Path(root) / name
            try:
                st = p.stat()
            except OSError:
                continue
            rel = str(p.relative_to(base_dir))
            entries.append((rel, int(st.st_mtime_ns), st.st_size))
    entries.sort()
    payload = json.dumps(
        {"plugin_module": plugin_module, "files": entries},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def default_cache_path(base_dir: Path, plugin_module: str) -> Path:
    safe = plugin_module.replace(".", "_")
    return base_dir.resolve() / ".caliper_cache" / f"{safe}_v{CACHE_SCHEMA_VERSION}.json"


def write_cache(
    path: Path,
    *,
    unified_model_dict: dict[str, Any],
    fingerprint: str,
    plugin_module: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "plugin_module": plugin_module,
        "input_fingerprint": fingerprint,
        "unified_model": unified_model_dict,
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def read_cache(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cache_is_valid(
    cached: dict[str, Any],
    *,
    expected_fingerprint: str,
    plugin_module: str,
) -> bool:
    if cached.get("schema_version") != CACHE_SCHEMA_VERSION:
        return False
    if cached.get("plugin_module") != plugin_module:
        return False
    if cached.get("input_fingerprint") != expected_fingerprint:
        return False
    return True
