"""
ScriptManager - Task registry and state management for DSL framework

Provides clean separation between task definitions and execution state.
"""

import logging

logger = logging.getLogger("DSL")


class TaskResult:
    """Container for task results that can be referenced in conditions"""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self._result = None
        self._executed = False

    @property
    def return_value(self):
        """Get the return value of the task"""
        return self._result

    def _set_result(self, result):
        self._result = result
        self._executed = True


class ScriptManager:
    """
    Manages task registration and execution state per script file

    Provides clean separation between task definitions and runtime state,
    avoiding global variable pollution and enabling better testing/isolation.
    """

    def __init__(self):
        # Task registry organized by source file path
        self._task_registry: dict[str, list[dict]] = {}
        # Task results organized by task name
        self._task_results: dict[str, TaskResult] = {}

    def register_task(self, task_info: dict, source_file: str) -> None:
        """
        Register a task from a specific source file

        Args:
            task_info: Dictionary containing task metadata
            source_file: Relative path to the source file defining the task
        """
        if source_file not in self._task_registry:
            self._task_registry[source_file] = []

        self._task_registry[source_file].append(task_info)

        # Create result container for this task
        task_name = task_info["name"]
        self._task_results[task_name] = TaskResult(task_name)

        logger.debug(f"Registered task '{task_name}' from {source_file}")

    def get_task_result(self, task_name: str) -> TaskResult | None:
        """Get the result container for a specific task"""
        return self._task_results.get(task_name)

    def get_tasks_from_file(self, source_file: str) -> list[dict]:
        """
        Get tasks from a specific source file

        Args:
            source_file: Relative path to the source file

        Returns:
            List of task info dictionaries from that file
        """
        return self._task_registry.get(source_file, [])

    def clear_tasks(self, source_file: str | None = None) -> None:
        """
        Clear tasks from registry

        Args:
            source_file: If specified, only clear tasks from this file.
                        If None, clear all tasks from all files.
        """
        if source_file is None:
            # Clear all tasks from all files
            logger.debug("Clearing all tasks from script manager")
            self._task_registry.clear()
            self._task_results.clear()
        else:
            # Clear tasks from specific file
            if source_file in self._task_registry:
                tasks_to_remove = self._task_registry[source_file]

                # Clear task results for tasks from this file
                for task_info in tasks_to_remove:
                    task_name = task_info["name"]
                    if task_name in self._task_results:
                        del self._task_results[task_name]

                # Remove tasks from this file
                del self._task_registry[source_file]
                logger.debug(f"Cleared {len(tasks_to_remove)} tasks from {source_file}")

    def get_registry_summary(self) -> dict[str, int]:
        """
        Get a summary of the current task registry

        Returns:
            Dictionary mapping source files to task counts
        """
        return {
            file_path: len(tasks) for file_path, tasks in self._task_registry.items()
        }

    def has_tasks(self) -> bool:
        """Check if any tasks are registered"""
        return bool(self._task_registry)

    def get_file_count(self) -> int:
        """Get the number of files with registered tasks"""
        return len(self._task_registry)

    def get_total_task_count(self) -> int:
        """Get the total number of registered tasks across all files"""
        return sum(len(tasks) for tasks in self._task_registry.values())


# Global script manager instance
# This provides the interface while keeping state encapsulated
_script_manager = ScriptManager()


def get_script_manager() -> ScriptManager:
    """Get the global script manager instance"""
    return _script_manager


def reset_script_manager() -> None:
    """Reset the global script manager (useful for testing)"""
    global _script_manager
    _script_manager = ScriptManager()
