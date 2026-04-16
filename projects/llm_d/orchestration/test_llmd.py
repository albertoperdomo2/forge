import pathlib
import logging

logger = logging.getLogger(__name__)

from projects.core.library import env, config, run

from projects.llm_d.toolbox.capture_isvc_state.main import run as capture_isvc_state


def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent)


@config.requires(
    ns="prepare.namespace.name",
    name="tests.llmd.flavors",
)
def test(_cfg):
    logger.warning(f"Hello test {_cfg.ns}/{_cfg.name}")

    # two alternatives to query the configuration:
    # @config.requires(dict) or config.project.get_config("<path>")
    # and we will define something similar for the secrets

    name = config.project.get_config("tests.llmd.flavors")

    capture_isvc_state(_cfg.name, namespace=_cfg.ns)
