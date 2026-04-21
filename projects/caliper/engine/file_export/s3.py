"""Upload files to S3-compatible storage."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _parallel_workers(requested: int, n_files: int) -> int:
    if n_files <= 0:
        return 1
    return max(1, min(requested, n_files))


def upload_tree(
    *,
    source: Path,
    paths: list[Path],
    bucket: str,
    prefix: str,
    tags: dict[str, str] | None = None,
    upload_workers: int = 10,
) -> str:
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError(
            "boto3 is required for S3 export. Install with: pip install -e '.[caliper]'"
        ) from e

    client = boto3.client("s3")
    root = source.resolve()
    tasks: list[tuple[Path, str]] = []
    for p in paths:
        if p.is_file():
            fp = p.resolve()
            if root.is_file():
                rel = Path(p.name)
            else:
                rel = fp.relative_to(root)
            key = f"{prefix.rstrip('/')}/{rel.as_posix()}"
            tasks.append((p, key))

    uploaded = len(tasks)
    workers = _parallel_workers(upload_workers, uploaded)

    def _upload(item: tuple[Path, str]) -> None:
        path, key = item
        client.upload_file(str(path), bucket, key)

    if workers <= 1:
        for item in tasks:
            _upload(item)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_upload, item) for item in tasks]
            for fut in as_completed(futures):
                fut.result()

    return f"s3://{bucket}/{prefix} ({uploaded} files)"
