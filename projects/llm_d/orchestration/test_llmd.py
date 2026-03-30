import pathlib
import logging
logger = logging.getLogger(__name__)

from projects.core.library import env, config, run

from projects.llm_d.toolbox.capture_isvc_state.main import run as capture_isvc_state

def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent)


def test():
    ns = config.project.get_config("prepare.namespace.name")
    name = config.project.get_config("tests.llmd.flavors")

    logger.warning(f"Hello prepare {ns}")

    capture_isvc_state(name, ns)
