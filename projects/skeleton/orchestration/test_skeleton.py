import logging
import pathlib

import yaml

from projects.core.library import config, env, run, vault
from projects.skeleton.toolbox.cluster_info.main import run as cluster_info

logger = logging.getLogger(__name__)


def init(strict_vault_validation=True):
    env.init()
    run.init()
    config.init(pathlib.Path(__file__).parent)
    vault.init(config.project.get_config("vaults"), strict=strict_vault_validation)


def test():
    logger.info("=== Skeleton Project Test Phase ===")

    if config.project.get_config("skeleton.deep_testing"):
        logger.warning("Running the (fake) deep testing ...")
    else:
        logger.warning("Running the (fake) light testing ...")

    client_id = vault.get_vault_content_path("psap-forge-notifications", "topsail-bot.clientid")
    if not client_id:
        logger.warning("`client_id` secret not available.")
    else:
        logger.warning(f"`client_id` secret available. Size: {client_id.stat().st_size}b")
        del client_id

    skeleton_config = config.project.get_config("skeleton", print=False)

    yaml_cfg = yaml.dump(
        {"skeleton": skeleton_config},
        indent=4,
        default_flow_style=False,
        sort_keys=False,
    )
    logger.info("")
    logger.info(f"Fake test configuration:\n{yaml_cfg}")

    if not config.project.get_config("skeleton.collect_cluster_info"):
        logger.warning("⚠️ Cluster information gathering not enabled. Returning early.")
        return 0

    # Demonstrate calling a toolbox from orchestration
    logger.info("Running cluster information toolbox...")

    result = cluster_info(output_format="text")

    if not result:
        logger.warning("⚠️ Cluster information gathering didn't work")
        return 1

    cluster_nodes_dest = getattr(result, "cluster_nodes_dest", None)
    if not cluster_nodes_dest:
        logger.warning("⚠️ Cluster information gathering didn't generate the cluster node file")
        return 1

    logger.info("✅ Cluster information gathering completed successfully")
    logger.info(f"Check {cluster_nodes_dest.parent} directory for detailed cluster information.")

    return 0
