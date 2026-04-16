"""
CLI argument parsing utilities for the DSL framework
"""

import argparse
import inspect
import re


def _parse_docstring_args(docstring: str) -> dict:
    """Parse function docstring to extract argument descriptions"""
    if not docstring:
        return {}

    # Look for Args: section
    args_match = re.search(r"Args:\s*\n(.*?)(?:\n\s*\n|\n\s*[A-Z]|\Z)", docstring, re.DOTALL)
    if not args_match:
        return {}

    args_section = args_match.group(1)
    arg_descriptions = {}

    # Parse each argument line
    for line in args_section.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue

        # Extract "param_name: description" format
        param_match = re.match(r"(\w+):\s*(.*)", line)
        if not param_match:
            continue

        param_name = param_match.group(1)
        description = param_match.group(2)
        arg_descriptions[param_name] = description

    return arg_descriptions


def create_dynamic_parser(func, positional_args=None) -> argparse.ArgumentParser:
    """
    Create argparse parser dynamically from function signature and docstring

    Args:
        func: Function to generate CLI for
        positional_args: List of parameter names to make positional (default: auto-detect)
    """

    # Get function signature and docstring
    sig = inspect.signature(func)
    docstring = inspect.getdoc(func)

    # Parse descriptions from docstring
    arg_descriptions = _parse_docstring_args(docstring)

    # Auto-detect positional args if not specified
    if positional_args is None:
        # Make first 2 parameters positional if they're commonly required
        param_names = [name for name in sig.parameters.keys() if name not in ("self", "cls")]
        positional_args = param_names[:2]  # First two parameters

    # Get main description from docstring
    main_description = docstring.split("\n")[0] if docstring else f"CLI for {func.__name__}"

    # Create parser
    parser = argparse.ArgumentParser(
        description=main_description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Generated automatically from {func.__name__}() signature.
        """.strip(),
    )

    # Add arguments based on function signature
    for param_name, param in sig.parameters.items():
        # Skip self/cls parameters
        if param_name in ("self", "cls"):
            continue

        # Determine if required (no default value)
        has_default = param.default != inspect.Parameter.empty

        # Get description from docstring
        help_text = arg_descriptions.get(param_name, f"{param_name} parameter")
        if has_default and param.default is not None:
            help_text += f" (default: {param.default})"

        # Determine argument type from annotation
        if param.annotation != inspect.Parameter.empty:
            if param.annotation is bool:
                # Boolean args are always optional flags
                cli_name = f"--{param_name.replace('_', '-')}"
                parser.add_argument(cli_name, action="store_true", dest=param_name, help=help_text)
                continue
            elif param.annotation in (str, int, float):
                arg_type = param.annotation
            else:
                arg_type = str  # Default to string
        else:
            arg_type = str  # Default to string

        # Add as positional or optional argument (or both!)
        if param_name in positional_args:
            # Add positional argument
            nargs = "?" if has_default else None  # Optional if has default
            default = param.default if has_default else None

            parser.add_argument(
                param_name,
                type=arg_type,
                nargs=nargs,
                default=default,
                help=f"{help_text} (positional)",
            )

            # ALSO add named version for flexibility
            cli_name = f"--{param_name.replace('_', '-')}"
            parser.add_argument(
                cli_name,
                type=arg_type,
                dest=param_name,  # Same destination as positional
                help=f"{help_text} (named alternative to positional)",
            )
        else:
            # Optional argument with --flag only
            cli_name = f"--{param_name.replace('_', '-')}"

            parser.add_argument(
                cli_name,
                type=arg_type,
                required=not has_default,
                dest=param_name,
                help=help_text,
            )

    return parser
