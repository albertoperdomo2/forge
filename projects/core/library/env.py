import logging
import os
import pathlib
import time

ARTIFACT_DIR = None
BASE_ARTIFACT_DIR = None  # Immutable copy of the initial ARTIFACT_DIR
FORGE_HOME = pathlib.Path(__file__).parents[3]


def _set_artifact_dir(value):
    global ARTIFACT_DIR
    ARTIFACT_DIR = value


def reset_artifact_dir():
    """Reset ARTIFACT_DIR to its original BASE_ARTIFACT_DIR value."""
    global ARTIFACT_DIR
    if BASE_ARTIFACT_DIR is not None:
        ARTIFACT_DIR = BASE_ARTIFACT_DIR
        os.environ["ARTIFACT_DIR"] = str(BASE_ARTIFACT_DIR)


def init(daily_artifact_dir=False):
    global ARTIFACT_DIR, BASE_ARTIFACT_DIR

    # Configure global logging to show INFO level messages
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        force=True,  # Override any existing basicConfig
    )

    if "ARTIFACT_DIR" in os.environ:
        artifact_dir = pathlib.Path(os.environ["ARTIFACT_DIR"])

    else:
        env_forge_base_dir = pathlib.Path(os.environ.get("FORGE_BASE_DIR", "/tmp"))

        artifact_dir = env_forge_base_dir / f"forge_{time.strftime('%Y%m%d-%H%M')}"

        artifact_dir.mkdir(parents=True, exist_ok=True)
        os.environ["ARTIFACT_DIR"] = str(artifact_dir)

    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Set BASE_ARTIFACT_DIR to the initial value (immutable)
    if BASE_ARTIFACT_DIR is None:
        BASE_ARTIFACT_DIR = artifact_dir
        # Also expose it as an environment variable
        os.environ["FORGE_BASE_ARTIFACT_DIR"] = str(BASE_ARTIFACT_DIR)

    _set_artifact_dir(artifact_dir)


def NextArtifactDir(name, *, lock=None, counter_p=None):
    if lock:
        with lock:
            next_count = counter_p[0]
            counter_p[0] += 1
    else:
        next_count = next_artifact_index()

    dirname = ARTIFACT_DIR / f"{next_count:03d}__{name}"

    return TempArtifactDir(dirname)


class TempArtifactDir:
    def __init__(self, dirname):
        self.dirname = pathlib.Path(dirname)
        self.previous_dirname = None

    def __enter__(self):
        self.previous_dirname = ARTIFACT_DIR
        os.environ["ARTIFACT_DIR"] = str(self.dirname)
        self.dirname.mkdir(exist_ok=True)

        _set_artifact_dir(self.dirname)

        return True

    def __exit__(self, ex_type, ex_value, exc_traceback):
        os.environ["ARTIFACT_DIR"] = str(self.previous_dirname)
        _set_artifact_dir(self.previous_dirname)

        return False  # If we returned True here, any exception would be suppressed!


def next_artifact_index():
    return len(list(ARTIFACT_DIR.glob("*__*")))
