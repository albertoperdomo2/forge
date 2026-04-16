"""
Kubernetes utilities for DSL tasks
"""

import re


def sanitize_k8s_name(name: str) -> str:
    """
    Sanitize a name to be compatible with Kubernetes object naming requirements.

    Kubernetes object names must:
    - Be lowercase only
    - Only contain alphanumeric characters and hyphens
    - Start and end with alphanumeric characters
    - Be maximum 63 characters long

    Args:
        name: The name to sanitize

    Returns:
        A valid Kubernetes object name

    Examples:
        >>> sanitize_k8s_name("My_Test Job!")
        "my-test-job-x"
        >>> sanitize_k8s_name("forge-llm_d-20260409-143022")
        "forge-llm-d-20260409-143022"
        >>> sanitize_k8s_name("valid-name123")
        "valid-name123"
    """
    # Convert to lowercase and replace invalid characters with hyphens
    sanitized = re.sub(r"[^a-z0-9\-]", "-", name.lower())

    # Remove leading/trailing hyphens and collapse multiple hyphens
    sanitized = re.sub(r"^-+|-+$", "", sanitized)
    sanitized = re.sub(r"-+", "-", sanitized)

    # Ensure it starts and ends with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "x" + sanitized
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + "x"

    # Truncate to 63 characters (K8s limit)
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
        # Make sure it still ends with alphanumeric after truncation
        if not sanitized[-1].isalnum():
            sanitized = sanitized[:-1] + "x"

    return sanitized or "default"


def is_valid_k8s_name(name: str) -> bool:
    """
    Check if a name is valid for Kubernetes objects.

    Args:
        name: The name to validate

    Returns:
        True if the name is valid, False otherwise

    Examples:
        >>> is_valid_k8s_name("valid-name123")
        True
        >>> is_valid_k8s_name("Invalid_Name")
        False
        >>> is_valid_k8s_name("toolongname" * 10)
        False
    """
    if not name:
        return False

    # Check length
    if len(name) > 63:
        return False

    # Check pattern: lowercase alphanumeric and hyphens, start/end with alphanumeric
    pattern = r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$"
    return bool(re.match(pattern, name))
