import logging

from projects.core.library import config
from projects.rhaiis.orchestration import runtime_config, test_phase

logger = logging.getLogger(__name__)

init = runtime_config.init


@config.requires(
    model_key="tests.rhaiis.model_key",
    workload_key="tests.rhaiis.workload_key",
    namespace="rhaiis.namespace",
)
def test(_cfg):
    model = runtime_config.get_model(_cfg.model_key)
    workload = runtime_config.get_workload(_cfg.workload_key)
    accelerator = runtime_config.get_accelerator()
    deploy_cfg = runtime_config.get_deploy_config()
    benchmark_cfg = runtime_config.get_benchmark_config()

    deployment_name = runtime_config.derive_deployment_name(model["hf_model_id"])
    vllm_image = runtime_config.get_vllm_image(accelerator)
    vllm_defaults = runtime_config.get_vllm_defaults()
    vllm_args = runtime_config.merge_vllm_args(vllm_defaults, model, workload)
    env_vars = runtime_config.merge_env_vars(accelerator, model)

    logger.info(
        f"Testing model={model['name']} workload={_cfg.workload_key} accelerator={accelerator}"
    )

    test_phase.run(
        deployment_name=deployment_name,
        namespace=_cfg.namespace,
        model_cfg=model,
        vllm_image=vllm_image,
        accelerator=accelerator,
        vllm_args=vllm_args,
        env_vars=env_vars,
        deploy_cfg=deploy_cfg,
        benchmark_cfg=benchmark_cfg,
        workload_data=workload["data"],
        rates=workload.get("rates", [1]),
        max_seconds=workload.get("max_seconds", 180),
    )
