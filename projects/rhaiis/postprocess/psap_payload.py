from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def generate_psap_payload(
    *,
    benchmarks_json_path: Path,
    model_id: str,
    vllm_image: str,
    vllm_args: dict[str, Any],
    accelerator: str,
    workload_key: str,
) -> dict[str, Any]:
    report = json.loads(benchmarks_json_path.read_text(encoding="utf-8"))

    image, tag = _split_image_tag(vllm_image)
    tp_size = int(vllm_args.get("tensor-parallel-size", 1))

    guidellm_start = None
    guidellm_end = None
    benchmarks = report.get("benchmarks", [])
    if benchmarks:
        starts = [b.get("start_time", 0) for b in benchmarks if b.get("start_time")]
        ends = [b.get("end_time", 0) for b in benchmarks if b.get("end_time")]
        if starts:
            guidellm_start = int(min(starts) * 1000)
        if ends:
            guidellm_end = int(max(ends) * 1000)

    return {
        "experiment_id": str(uuid.uuid4()).upper(),
        "experiment_type": "perf",
        "model": model_id,
        "inference_server": "vllm",
        "inference_server_version": tag,
        "container_image": image,
        "container_image_tag": tag,
        "container_entrypoint": None,
        "inference_server_args": dict(vllm_args),
        "accelerator_type": accelerator.upper(),
        "accelerator_count": tp_size,
        "accelerator_memory_gb": 0,
        "machine_type": None,
        "provider": "redhat",
        "report": report,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "guidellm_start_time_ms": guidellm_start,
        "guidellm_end_time_ms": guidellm_end,
    }


def write_psap_payload(
    *,
    payload: dict[str, Any],
    output_dir: Path,
    accelerator: str,
    model_id: str,
    workload_key: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_short = model_id.rsplit("/", 1)[-1].lower().replace(".", "-")
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"PSAP_perf_{workload_key}_{accelerator}_{model_short}_{date_str}.json"
    path = output_dir / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("PSAP payload written to %s", path)
    return path


def _split_image_tag(full_image: str) -> tuple[str, str]:
    if ":" in full_image:
        parts = full_image.rsplit(":", 1)
        return parts[0], parts[1]
    return full_image, "latest"
