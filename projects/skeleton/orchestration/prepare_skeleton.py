import logging
import pathlib

from projects.core.library import config

logger = logging.getLogger(__name__)


def prepare():
    logger.info("=== Skeleton Project Prepare Phase ===")

    try:
        config_file_content = pathlib.Path(config.project.config_path).read_text()
        logger.info(f"Configuration file: {config_file_content}")

        logger.info("✅ Prepare phase completed successfully")
        return 0

    except Exception as e:
        logger.error(f"❌ Error during prepare phase: {e}")
        return 1


def cleanup():
    logger.info("=== Skeleton Project Cleanup Phase ===")
    logger.info("Demonstrating basic cleanup operations")

    try:
        logger.info("✅ Cleanup phase completed successfully")
        return 0
    except Exception as e:
        logger.error(f"❌ Error during cleanup phase: {e}")
        return 1
