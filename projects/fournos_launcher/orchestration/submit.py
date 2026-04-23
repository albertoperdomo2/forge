import logging
import os
import pathlib
import signal

from projects.core.library import config, env, run, vault
from projects.fournos_launcher.orchestration import job_management
from projects.fournos_launcher.toolbox.submit_and_wait.main import (
    run as submit_and_wait,
)

logger = logging.getLogger(__name__)


def _signal_handler_sigint(sig, frame):
    """Handle SIGINT (Ctrl+C) for FOURNOS launcher."""
    print("\n🚫 FOURNOS launcher received SIGINT - shutting down jobs...")
    env.reset_artifact_dir()
    job_management.shutdown_fjobs_on_interrupt()
    # Don't call sys.exit here - let the original handler handle it


def _signal_handler_sigterm(sig, frame):
    """Handle SIGTERM for FOURNOS launcher."""
    print("\n🛑 FOURNOS launcher received SIGTERM - shutting down jobs...")
    env.reset_artifact_dir()
    job_management.shutdown_fjobs_on_interrupt()
    # Don't call sys.exit here - let the original handler handle it


def _setup_signal_handlers():
    """Set up signal handlers for FOURNOS job shutdown."""
    try:
        # Store original handlers
        original_sigint = signal.signal(signal.SIGINT, _signal_handler_sigint)
        original_sigterm = signal.signal(signal.SIGTERM, _signal_handler_sigterm)

        logger.debug("FOURNOS signal handlers installed")

        # Store references so we can restore them if needed
        _setup_signal_handlers._original_sigint = original_sigint
        _setup_signal_handlers._original_sigterm = original_sigterm

    except Exception as e:
        logger.warning(f"Failed to set up FOURNOS signal handlers: {e}")


def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent, apply_config_overrides=False)
    config.project.apply_config_overrides(ignore_not_found=True)
    config.project.filter_out_used_overrides()
    vault.init(config.project.get_config("vaults"))

    prepare_env()


def prepare_env():
    kubeconfig_path = vault.get_vault_content_path(
        config.project.get_config("fournos.kubeconfig.vault.name"),
        config.project.get_config("fournos.kubeconfig.vault.key"),
    )

    os.environ["KUBECONFIG"] = str(kubeconfig_path)


def submit_job():
    # Set up signal handlers for graceful job shutdown on interruption
    _setup_signal_handlers()

    overrides = {}
    overrides.update(config.project.get_config("overrides"))
    overrides.update(config.project.get_config("extra_overrides"))

    # Build env dict from pass lists
    env_dict = {}
    env_pass_lists = config.project.get_config("fournos.job.env", print=False)
    for _, pass_list in (env_pass_lists or {}).items():
        for env_var in pass_list:
            if env_var in os.environ:
                env_dict[env_var] = os.environ[env_var]

    # Add extra environment variables
    extra_env = config.project.get_config("fournos.job.extra_env", {}, print=False)
    env_dict.update(extra_env)

    # Update display name with project and args
    project_name = config.project.get_config("ci_job.project")
    job_args = config.project.get_config("ci_job.args")

    # job_args is always a list, format accordingly
    args_str = " ".join(job_args)

    display_name = f"{project_name} {args_str}".strip()
    config.project.set_config("fournos.job.display_name", display_name)
    logger.info(f"Set job display name: {display_name}")

    # Validate required configuration before job submission
    cluster_name = config.project.get_config("cluster.name")
    if not cluster_name:
        raise ValueError(
            "cluster.name must be configured in config.yaml - cannot submit job without target cluster"
        )

    submit_and_wait(
        cluster_name=cluster_name,
        project=config.project.get_config("ci_job.project"),
        args=config.project.get_config("ci_job.args"),
        variables_overrides=overrides,
        namespace=config.project.get_config("fournos.namespace"),
        owner=config.project.get_config("fournos.job.owner"),
        display_name=config.project.get_config("fournos.job.display_name"),
        pipeline_name=config.project.get_config("fournos.job.pipeline_name"),
        env=env_dict,
        status_dest=env.ARTIFACT_DIR,
        ci_label=config.project.get_config("fournos.job.ci_label"),
    )

    return 0
