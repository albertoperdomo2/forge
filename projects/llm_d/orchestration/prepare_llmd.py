import logging

from projects.core.library import config

logger = logging.getLogger(__name__)


def prepare():
    ns = config.project.get_config("prepare.namespace.name")
    logger.warning(f"Hello prepare {ns}")
    pass


def cleanup():
    logger.warning("Hello cleanup")
    pass
