# llm_d

`llm_d` is the Forge project for validating downstream llm-d on RHOAI.

The current implementation is intentionally narrow:

- target only downstream `LLMInferenceService`
- keep the public interface compatible with current Fournos phase execution
- use checked-in presets and manifests instead of a large mutable config surface

Main entrypoints:

- CI phase wrapper: [ci.py](/Users/aperdomo/workspace/redhat/forge/projects/llm_d/orchestration/ci.py)
- Prepare flow: [prepare_llmd.py](/Users/aperdomo/workspace/redhat/forge/projects/llm_d/orchestration/prepare_llmd.py)
- Test flow: [test_llmd.py](/Users/aperdomo/workspace/redhat/forge/projects/llm_d/orchestration/test_llmd.py)
- Shared runtime/config loader: [llmd_runtime.py](/Users/aperdomo/workspace/redhat/forge/projects/llm_d/orchestration/llmd_runtime.py)
