# Quickstart: Toolbox DSL command

**Feature**: 008-toolbox-dsl

## Prerequisites

- Repository root as working directory (matches task path keys and `FORGE_HOME` resolution).
- FORGE environment initialized as existing toolbox commands do.

## Minimal pattern

1. **Public entrypoint** — typed/documented parameters your orchestration will pass.
2. **Task functions** — small steps using `(args, ctx)`.
3. **Properties** — attach `@task` plus optional `@when`, `@retry`, `@always`.

```python
from projects.core.dsl import always, execute_tasks, retry, task, when

def run(my_flag: bool = False):
    """Run this toolbox command.

    Args:
        my_flag: Example flag passed from orchestration or CLI.
    """
    return execute_tasks(locals())


@task
def prepare(args, ctx):
    ctx.ready = True
    return True


@when(lambda: prepare.status.return_value is True)
@task
def only_if_ready(args, ctx):
    return "ok"


@retry(attempts=3, delay=1, backoff=1.0)
@task
def wait_for_cluster(args, ctx):
    # return truthy when ready, falsy to retry (example stub)
    return True


@always
@task
def cleanup(args, ctx):
    pass
```

## Run

- **Python**: call `run(my_flag=True)` from orchestration.
- **CLI**: wire `create_toolbox_main(run)` (see `projects.core.dsl.toolbox`).

## Where to read more

- Authoring contract: [contracts/toolbox_dsl_authoring.md](./contracts/toolbox_dsl_authoring.md)
- Operator-facing prose: `docs/toolbox/dsl.md`
