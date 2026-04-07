import pathlib
import logging
logger = logging.getLogger(__name__)

from projects.core.library import env, config, run

def init():
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent)

def test():
    logger.info("Hello test skeleton")
    return 0