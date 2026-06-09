# llm_d

`llm_d` is the Forge project for validating downstream llm-d on RHOAI.

The current implementation is intentionally narrow:

- target only downstream `LLMInferenceService`
- keep the public interface compatible with current Fournos phase execution
- use checked-in config chunks and manifests instead of a large mutable config surface

Configuration layout:

- project config chunk: [`orchestration/config.d/project.yaml`](./orchestration/config.d/project.yaml)
- config chunks: [`orchestration/config.d`](./orchestration/config.d)
- presets: [`orchestration/presets.d`](./orchestration/presets.d)
- manifests: [`orchestration/manifests`](./orchestration/manifests)

Main entrypoints:

- CI phase wrapper: [`orchestration/ci.py`](./orchestration/ci.py)
- CLI wrapper: [`orchestration/cli.py`](./orchestration/cli.py)
- Shared runtime/config loader: [`orchestration/runtime_config.py`](./orchestration/runtime_config.py)
- Prepare flow: [`orchestration/prepare_sequence.py`](./orchestration/prepare_sequence.py)
- Test flow: [`orchestration/test_phase.py`](./orchestration/test_phase.py)
- Cleanup flow: [`orchestration/cleanup_phase.py`](./orchestration/cleanup_phase.py)

Profile model:

- deployment profiles are represented as presets that primarily select the scheduler mode
- benchmark profiles are represented as named entries under
  [`orchestration/config.d/workloads.yaml`](./orchestration/config.d/workloads.yaml)

Current deployment presets:

- `deployment-approximate-prefix-cache`
- `deployment-precise-prefix-cache`
- `deployment-distributed-default`

Existing smoke presets extend those deployment presets and keep the model and smoke request
selection.

Benchmark usage:

- select a deployment preset on the `/test` line
- select a benchmark workload with `/var runtime.benchmark_key: ...`
- select the model explicitly with `/var runtime.model_key: ...` when needed

Example:

```text
/test fournos llm_d deployment-precise-prefix-cache
/cluster athena-fire
/var runtime.model_key: llama-3-1-8b-instruct-fp8
/var runtime.benchmark_key: heavy-heterogeneous
```

Benchmark adaptation notes:

- deployment profiles are intentionally reduced to scheduler selection in the current Forge shape
- benchmark workloads are adapted to the existing GuideLLM execution model
- multi-rate benchmarks expand into one GuideLLM run per rate
- expressions such as `{2*rate}` and `{10*rate}` are resolved per run
- Benchflow-specific features such as pre-warmup and env passthrough are not modeled yet
