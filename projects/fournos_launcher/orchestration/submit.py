import pathlib
import logging
logger = logging.getLogger(__name__)

import os

from projects.core.library import env, config, run

from projects.fournos_launcher.toolbox.submit_and_wait.main import run as submit_and_wait

def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent, apply_config_overrides=False)
    config.project.apply_config_overrides(ignore_not_found=True)
    config.project.filter_out_used_overrides()


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
