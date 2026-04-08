import pathlib
import logging
logger = logging.getLogger(__name__)

import os

from projects.core.library import env, config, run

from projects.fournos_launcher.toolbox.submit_and_wait.main import run as submit_and_wait

def filter_out_launcher_overrides():
    """Remove the config fields that apply to FOURNOS, keep only
    those that we want to pass to the FOURNOS job"""

    overrides = config.project.get_config("overrides", {})
    new_overrides = {}
    for key, value in overrides.items():
        if config.project.has_config(key):
            continue
        new_overrides[key] = value

    config.project.set_config("overrides", new_overrides, print=False)


def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent, apply_config_overrides=False)
    config.project.apply_config_overrides(ignore_not_found=True)
    filter_out_launcher_overrides()


def submit_job():

    os.environ["KUBECONFIG"] = str(pathlib.Path(os.environ["PSAP_FORGE_FOURNOS_CI_SECRET_PATH"]) / "kubeconfig")

    submit_and_wait(
      cluster_name=config.project.get_config("cluster.name"),
      project=config.project.get_config("ci_job.project"),
      args=config.project.get_config("ci_job.args"),
      variables_overrides=config.project.get_config("overrides"),
      namespace=config.project.get_config("fournos.namespace"),
    )

    return 0
