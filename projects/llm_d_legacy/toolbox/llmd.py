import sys
import logging

from projects.legacy.library.ansible_toolbox import (
    RunAnsibleRole,
    AnsibleRole,
    AnsibleMappedParams,
    AnsibleConstant,
    AnsibleSkipConfigGeneration,
)


class Llmd:
    """
    Commands and utilities for the LLM-D toolbox
    """

    @AnsibleRole("llmd_deploy_gateway")
    @AnsibleMappedParams
    def deploy_gateway(
        self,
        name="openshift-ai-inference",
        gateway_class="data-science-gateway-class",
        namespace="openshift-ingress",
    ):
        """
        Deploys a GatewayClass and Gateway object

        Default gateway class is created by the DSCI -> GatewayConfig/default-gateway -> GatewayClass/data-science-gateway-class

        Args:
          name: Name of the gateway to deploy
          gateway_class: Name of the gateway class to deploy
          namespace: Namespace where the gateway will be deployed
        """

        if name != "openshift-ai-inference":
            logging.error("Currently the gateway name must be 'openshift-ai-inference'")
            raise SystemExit(1)

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_deploy_llm_inference_service")
    @AnsibleMappedParams
    def deploy_llm_inference_service(self, name, namespace, yaml_file):
        """
        Deploys an LLM InferenceService from a YAML file

        Args:
          name: Name of the inference service to deploy
          namespace: Namespace to deploy the inference service in
          yaml_file: Path to the YAML file containing the LLMInferenceService
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_run_guidellm_benchmark")
    @AnsibleMappedParams
    def run_guidellm_benchmark(
        self,
        endpoint_url,
        name="guidellm-benchmark",
        namespace="",
        image="ghcr.io/vllm-project/guidellm",
        version="v0.6.0",
        timeout=900,
        pvc_size="1Gi",
        guidellm_args=[],
        run_as_root=False,
    ):
        """
        Runs a Guidellm benchmark job against the LLM inference service

        Args:
          endpoint_url: Endpoint URL for the LLM inference service to benchmark
          name: Name of the benchmark job
          namespace: Namespace to run the benchmark job in (empty string auto-detects current namespace)
          image: Container image for the benchmark
          version: Version tag for the benchmark image
          timeout: Timeout in seconds to wait for job completion
          pvc_size: Size of the PersistentVolumeClaim for storing results
          guidellm_args: List of additional guidellm arguments (e.g., ["--rate=10", "--max-seconds=30"])
          run_as_root: Run the GuideLLM container as root user
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_capture_isvc_state")
    @AnsibleMappedParams
    def capture_isvc_state(self, llmisvc_name, namespace=""):
        """
        Captures all relevant objects and state for an LLMInferenceService

        Args:
          llmisvc_name: Name of the LLMInferenceService to capture
          namespace: Namespace of the LLMInferenceService (empty string auto-detects current namespace)
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("storage_download_to_pvc")
    @AnsibleMappedParams
    def download_to_pvc(
        self,
        name,
        source,
        pvc_name,
        namespace,
        creds="",
        storage_dir="/",
        clean_first=False,
        pvc_access_mode="ReadWriteOnce",
        pvc_size="80Gi",
        pvc_storage_class_name=None,
        image="registry.access.redhat.com/ubi9/ubi",
        run_as_root=False,
    ):
        """
        Downloads the a dataset into a PVC of the cluster

        Args:
            name: Name of the data source
            source: URL of the source data
            pvc_name: Name of the PVC that will be create to store the dataset files.
            namespace: Name of the namespace in which the PVC will be created
            creds: Path to credentials to use for accessing the dataset.
            clean_first: if True, clears the storage directory before downloading.
            storage_dir: the path where to store the downloaded files, in the PVC
            pvc_access_mode: the access mode to request when creating the PVC
            pvc_size: the size of the PVC to request, when creating the PVC
            pvc_storage_class_name: the name of the storage class to pass when creating the PVC
            image: the image to use for running the download Pod
            run_as_root: Run the download container as root user
        """

        return RunAnsibleRole(locals())
