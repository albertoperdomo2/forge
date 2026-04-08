import pathlib
import logging
logger = logging.getLogger(__name__)

import os

from projects.core.library import env, config, run, vault

from projects.fournos_launcher.toolbox.submit_and_wait.main import run as submit_and_wait

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
        config.project.get_config("fournos.kubeconfig.vault.key")
    )

    os.environ["KUBECONFIG"] = str(kubeconfig_path)


def submit_job():
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

    submit_and_wait(
      cluster_name=config.project.get_config("cluster.name"),
      project=config.project.get_config("ci_job.project"),
      args=config.project.get_config("ci_job.args"),
      variables_overrides=overrides,
      namespace=config.project.get_config("fournos.namespace"),
      owner=config.project.get_config("fournos.job.owner"),
      display_name=config.project.get_config("fournos.job.display_name"),
      pipeline_name=config.project.get_config("fournos.job.pipeline_name"),
      env=env_dict,
    )

    return 0
