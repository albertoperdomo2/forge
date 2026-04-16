import pathlib
import logging

logger = logging.getLogger(__name__)
import os
import shutil

from projects.core.library import env, config, run
from projects.core.ci_entrypoint import run_ci


def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent)


def prepare():
    foreign_repo_id = os.environ.get("PSAP_FORGE_FOREIGN_TESTING")
    repo_owner = os.environ.get("REPO_OWNER")
    repo_name = os.environ.get("REPO_NAME")
    pull_pull_sha = os.environ.get("PULL_PULL_SHA")

    if not foreign_repo_id:
        raise ValueError(
            "PSAP_FORGE_FOREIGN_TESTING must be set (and point to `foreign_testing.$NAME` field)"
        )

    foreign_repo_configs = config.project.get_config("foreign_testing")
    foreign_repo_config = foreign_repo_configs.get(foreign_repo_id, None)
    if foreign_repo_config is None:
        raise ValueError(
            f"PSAP_FORGE_FOREIGN_TESTING must point to `foreign_testing.{foreign_repo_id}` field"
        )

    repo_dest = env.FORGE_HOME / "foreign_testing" / repo_name
    run.run(f'git clone "https://github.com/{repo_owner}/{repo_name}" "{repo_dest}"')
    run.run(f'git -C "{repo_dest}" fetch --quiet origin "{pull_pull_sha}"')
    run.run(f'git -C "{repo_dest}" reset --hard FETCH_HEAD')

    # Copy foreign projects to FORGE home
    forge_projects_dir = env.FORGE_HOME / "projects"
    forge_projects_dir.mkdir(parents=True, exist_ok=True)

    for project_name, project_src in foreign_repo_config["project_mappings"].items():
        src_path = repo_dest / project_src
        dest_path = forge_projects_dir / project_name

        logger.info(f"Copying foreign project: {src_path} -> {dest_path}")

        if not src_path.exists():
            logger.warning(f"Source path not found: {src_path}")
            raise FileNotFoundError(f"Foreign project source not found: {src_path}")

        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)

    return repo_dest


def submit(project_path=None):
    """
    Submit a FOURNOS deployment job

    Args:
        project_path: Path to the project source directory (will be passed as --project-source)
    """
    # Build the command arguments
    args = ["deploy"]

    if project_path:
        args = [*["--project-source", str(project_path)], *args]
        logger.info(f"Submitting deployment with args: {args}")

    run_ci.execute_project_operation(
        "fournos_deploy",
        "ci",
        args,
        do_prepare_ci=False,
        verbose=True,
    )
