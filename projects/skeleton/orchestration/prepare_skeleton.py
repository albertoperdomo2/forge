import logging
logger = logging.getLogger(__name__)

def prepare():
    logger.info("Hello prepare skeleton")
    return 0

def cleanup():
    logger.info("Hello cleanup skeleton")
    return 0