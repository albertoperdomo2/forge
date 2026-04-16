"""
Context management for DSL tasks

Provides readonly args and mutable context for task execution.
"""

import types
from typing import Any


class ReadOnlyArgs:
    """
    A readonly wrapper around the args object that prevents modification
    """

    def __init__(self, args_dict: dict):
        # Store the original args in a private attribute
        object.__setattr__(self, "_args_dict", args_dict)

    def __getattr__(self, name: str) -> Any:
        args_dict = object.__getattribute__(self, "_args_dict")
        if name in args_dict:
            return args_dict[name]
        raise AttributeError(f"'ReadOnlyArgs' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"Cannot modify readonly args. Attempted to set '{name}' = {value}"
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"Cannot delete attribute '{name}' from readonly args")

    def __contains__(self, name: str) -> bool:
        args_dict = object.__getattribute__(self, "_args_dict")
        return name in args_dict

    def __repr__(self) -> str:
        args_dict = object.__getattribute__(self, "_args_dict")
        return f"ReadOnlyArgs({args_dict})"


class TaskContext:
    """
    Mutable context for values defined within a task
    """

    def __init__(self):
        pass

    def __repr__(self) -> str:
        attrs = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return f"TaskContext({attrs})"


def create_task_parameters(
    original_args: types.SimpleNamespace, shared_context: types.SimpleNamespace
) -> tuple[ReadOnlyArgs, TaskContext]:
    """
    Create readonly args and mutable context from the original args object

    Args:
        original_args: The original args SimpleNamespace from execute_tasks
        shared_context: The shared context that persists across tasks

    Returns:
        Tuple of (readonly_args, mutable_context)
    """
    # Convert SimpleNamespace to dict for ReadOnlyArgs (only original args, not context)
    args_dict = vars(original_args)

    readonly_args = ReadOnlyArgs(args_dict)

    # Create a TaskContext that wraps the shared context
    # This allows the task to modify the shared context
    context = TaskContext()

    # Copy existing values from shared context to this task's context
    for attr_name, attr_value in vars(shared_context).items():
        if not attr_name.startswith("_"):
            setattr(context, attr_name, attr_value)

    return readonly_args, context
