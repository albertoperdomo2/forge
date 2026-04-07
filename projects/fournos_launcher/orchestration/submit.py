import pathlib
import logging
logger = logging.getLogger(__name__)

import os

from projects.core.library import env, config, run


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


def submit():
    logger.warning(f"Hello Fournos")

    os.environ["KUBECONFIG"] = str(pathlib.Path(os.environ["PSAP_FORGE_FOURNOS_CI_SECRET_PATH"]) / "kubeconfig")

    run.run("oc get fjobs")

    return 0
