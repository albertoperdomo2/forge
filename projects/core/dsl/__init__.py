"""
Task-based DSL for FORGE operations
"""

from .task import task, retry, when, always
from .runtime import execute_tasks, clear_tasks
from . import shell
from . import toolbox
from . import template
from . import context

__all__ = ['always', 'clear_tasks', 'context', 'execute_tasks', 'retry', 'shell', 'task', 'template', 'when']
