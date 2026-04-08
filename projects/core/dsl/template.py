"""
Template rendering utilities for DSL tasks

This module provides helpers for loading and rendering Jinja2 templates
in FORGE toolbox tasks.
"""

import jinja2
import inspect
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from .log import logger

def render_template(template_name: str, context: Optional[Dict[str, Any]] = None, templates_dir: Optional[Path] = None) -> str:
    """
    Render a Jinja2 template with the given context

    Args:
        template_name: Name of the template file (e.g., "job.yaml.j2")
        context: Dictionary of variables to pass to the template. If None, auto-detects
                args and context from calling task.
        templates_dir: Directory containing templates. If None, looks for a "templates"
                      directory relative to the calling module.

    Returns:
        Rendered template as a string

    Example:
        @task
        def create_manifest(args, context):
            # Auto-detects args and context
            content = render_template("job.yaml.j2")
            # Or with explicit context
            content = render_template("job.yaml.j2", {"args": args, "custom": "value"})
    """
    # Auto-detect context if not provided
    if context is None:
        context = _get_task_context()

    if templates_dir is None:
        # Find templates directory relative to the task that's calling us
        frame = inspect.currentframe()

        # Walk up the call stack to find the task function
        while frame:
            frame = frame.f_back
            if frame is None:
                break

            local_vars = frame.f_locals

            # Check if this frame looks like a task (has args and context/ctx)
            context_var = None
            if 'context' in local_vars:
                context_var = local_vars['context']
            elif 'ctx' in local_vars:
                context_var = local_vars['ctx']

            if 'args' in local_vars and context_var is not None:
                # This looks like a task frame - use its file location
                caller_file = Path(frame.f_code.co_filename)
                templates_dir = caller_file.parent / "templates"
                break

        # Fallback: use immediate caller if we can't find a task
        if templates_dir is None:
            caller_frame = inspect.currentframe().f_back
            caller_file = Path(caller_frame.f_code.co_filename)
            templates_dir = caller_file.parent / "templates"

    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    # Set up Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        # Enable auto-escaping for security (though we're generating YAML, not HTML)
        autoescape=jinja2.select_autoescape(['html', 'xml']),
        # Raise errors for undefined variables instead of silently ignoring
        undefined=jinja2.StrictUndefined,
        # Keep line endings consistent
        keep_trailing_newline=True
    )

    # Add custom YAML filter
    def toyaml_filter(value, flow_style=False, default_flow_style=None, indent_by=0):
        """Convert value to YAML format with proper indentation"""
        # Use flow_style parameter if provided, otherwise use default_flow_style
        if default_flow_style is None:
            default_flow_style = flow_style

        yaml_output = yaml.dump(value, default_flow_style=default_flow_style, sort_keys=False).rstrip()

        if indent_by > 0:
            # Add indentation to each line except the first
            lines = yaml_output.split('\n')
            if len(lines) > 1:
                indented_lines = [lines[0]]  # First line keeps original indentation
                for line in lines[1:]:
                    if line.strip():  # Don't indent empty lines
                        indented_lines.append(' ' * indent_by + line)
                    else:
                        indented_lines.append(line)
                yaml_output = '\n'.join(indented_lines)

        return yaml_output

    env.filters['toyaml'] = toyaml_filter

    try:
        template = env.get_template(template_name)
        return template.render(context)
    except jinja2.TemplateNotFound as e:
        available_templates = [t for t in templates_dir.glob("*.j2")]
        raise FileNotFoundError(
            f"Template '{template_name}' not found in {templates_dir}. "
            f"Available templates: {[t.name for t in available_templates]}"
        ) from e
    except jinja2.TemplateError as e:
        raise RuntimeError(f"Template rendering error in '{template_name}': {e}") from e


def _get_task_context() -> Dict[str, Any]:
    """
    Auto-detect args and context from the calling task function

    Walks up the call stack to find a function call with 'args' and 'context'/'ctx' parameters,
    which indicates it's being called from a DSL task.

    Returns:
        Dictionary with 'args' and 'context' from the calling task
    """
    frame = inspect.currentframe()

    # Walk up the call stack looking for a function with args and context
    while frame:
        frame = frame.f_back
        if frame is None:
            break

        local_vars = frame.f_locals

        # Check if this frame has both 'args' and 'context'/'ctx' - indicates it's a task
        context_var = None
        if 'context' in local_vars:
            context_var = local_vars['context']
        elif 'ctx' in local_vars:
            context_var = local_vars['ctx']

        if 'args' in local_vars and context_var is not None:
            return {
                'args': local_vars['args'],
                'ctx': context_var
            }

    # If we can't find args and context, return empty dict
    # This allows the function to work even outside of tasks
    return {}


def render_template_to_file(template_name: str, output_file: Path,
                           extra_context: Optional[Dict[str, Any]] = None,
                           templates_dir: Optional[Path] = None) -> Path:
    """
    Render a template directly to a file with automatic args/context detection

    Args:
        template_name: Name of the template file
        output_file: Path where rendered content should be written
        extra_context: Additional variables to pass to template (optional)
        templates_dir: Directory containing templates (auto-detected if None)

    Returns:
        Path to the created file

    Example:
        @task
        def create_manifest(args, context):
            manifest_path = args.artifact_dir / "manifest.yaml"
            # Automatically uses args and context from the calling task
            render_template_to_file("job.yaml.j2", manifest_path)
    """
    # Auto-detect args and context from calling task
    context = _get_task_context()

    # Add any extra context provided
    if extra_context:
        context.update(extra_context)

    logger.info("== render_template_to_file ==")
    logger.info(f"| <src> {template_name}")
    logger.info(f"| <dst> {output_file}")
    logger.info("==")

    rendered_content = render_template(template_name, context, templates_dir)

    with open(output_file, 'w') as f:
        f.write(rendered_content)

    return output_file


def get_templates_dir(relative_to_file: Optional[str] = None) -> Path:
    """
    Get the templates directory relative to a file

    Args:
        relative_to_file: File path to use as reference. If None, uses the calling module.

    Returns:
        Path to the templates directory

    Example:
        templates_dir = get_templates_dir(__file__)
        # Returns: /path/to/current/module/templates/
    """
    if relative_to_file is None:
        caller_frame = inspect.currentframe().f_back
        relative_to_file = caller_frame.f_code.co_filename

    return Path(relative_to_file).parent / "templates"


def list_templates(templates_dir: Optional[Path] = None) -> list[str]:
    """
    List available templates in a directory

    Args:
        templates_dir: Directory to scan for templates (auto-detected if None)

    Returns:
        List of template filenames

    Example:
        templates = list_templates()
        print(f"Available templates: {templates}")
    """
    if templates_dir is None:
        caller_frame = inspect.currentframe().f_back
        caller_file = Path(caller_frame.f_code.co_filename)
        templates_dir = caller_file.parent / "templates"

    if not templates_dir.exists():
        return []

    return [t.name for t in templates_dir.glob("*.j2")]
