"""Parse orchestration: traverse → plugin → unified model → cache."""

from __future__ import annotations

from pathlib import Path

from projects.caliper.engine.cache import (
    cache_is_valid,
    default_cache_path,
    fingerprint_base_dir,
    read_cache,
    write_cache,
)
from projects.caliper.engine.model import UnifiedRunModel
from projects.caliper.engine.traverse import discover_test_bases
from projects.caliper.engine.validation import model_from_jsonable, model_to_jsonable


def run_parse(
    *,
    base_dir: Path,
    plugin_module: str,
    plugin: object,
    use_cache: bool,
    cache_path: Path | None,
    force_report_partial: bool = True,
) -> UnifiedRunModel:
    """
    Run full parse or load valid cache.

    plugin must implement parse(base_dir, nodes).
    """
    base_dir = base_dir.resolve()
    path = cache_path or default_cache_path(base_dir, plugin_module)
    fp = fingerprint_base_dir(base_dir, plugin_module)

    if use_cache:
        raw = read_cache(path)
        if raw is not None and cache_is_valid(
            raw, expected_fingerprint=fp, plugin_module=plugin_module
        ):
            return model_from_jsonable(raw["unified_model"])

    nodes = discover_test_bases(base_dir)
    parse_fn = plugin.parse
    result = parse_fn(base_dir, nodes)
    records = result.records
    warnings = getattr(result, "warnings", [])

    model = UnifiedRunModel(
        plugin_module=plugin_module,
        base_directory=str(base_dir),
        test_nodes=nodes,
        unified_result_records=records,
        parse_cache_ref=str(path),
    )
    if warnings and force_report_partial:
        for w in warnings:
            print(f"[parse warning] {w}")  # noqa: T201 — CLI feedback

    unified_dict = model_to_jsonable(model)
    write_cache(
        path,
        unified_model_dict=unified_dict,
        fingerprint=fp,
        plugin_module=plugin_module,
    )
    model.parse_cache_ref = str(path)
    return model
