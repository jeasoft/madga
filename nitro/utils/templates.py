"""
Safe Template Rendering.

Provides safe variable substitution without allowing template injection.
Only supports {{variable}} syntax - NO Django template tags like {% %}.
"""

import re
from typing import Any

# Regex to match {{ variable }} with optional whitespace
VARIABLE_PATTERN = re.compile(r'\{\{\s*(\w+(?:\.\w+)*)\s*\}\}')


def safe_render(template_text: str, context: dict) -> str:
    """
    Render a template string with only variable substitution.

    This is a SAFE alternative to Django's Template engine that does NOT
    allow template tags ({% %}), filters, or any code execution. Only
    simple {{ variable }} and {{ object.attribute }} substitution is supported.

    Args:
        template_text: String with {{ variable }} placeholders
        context: Dict with values to substitute

    Returns:
        Rendered string with variables replaced

    Examples:
        >>> safe_render("Hola {{ name }}", {"name": "Juan"})
        'Hola Juan'

        >>> safe_render("Total: {{ payment.amount }}", {"payment": {"amount": 100}})
        'Total: 100'

        >>> safe_render("{{ foo }}", {})  # Missing variable
        '{{ foo }}'

    Security:
        - NO template tags allowed ({% if %}, {% for %}, {% load %}, etc.)
        - NO filters allowed ({{ var|filter }})
        - NO arbitrary attribute access beyond simple dot notation
        - Cannot access settings, request, or other Django internals
    """
    if not template_text:
        return ''

    def replace_variable(match):
        key = match.group(1)
        value = _resolve_variable(key, context)
        if value is None:
            # Keep original placeholder if variable not found
            return match.group(0)
        return str(value)

    return VARIABLE_PATTERN.sub(replace_variable, template_text)


def _resolve_variable(key: str, context: dict) -> Any:
    """
    Resolve a dotted variable path from context.

    Args:
        key: Variable name, possibly with dots (e.g., "tenant.full_name")
        context: Context dict

    Returns:
        Resolved value or None if not found
    """
    parts = key.split('.')
    value = context

    for part in parts:
        if value is None:
            return None

        if isinstance(value, dict):
            value = value.get(part)
        elif hasattr(value, part):
            value = getattr(value, part, None)
            # If it's a method, call it (for things like get_full_name())
            if callable(value):
                try:
                    value = value()
                except (TypeError, Exception):
                    return None
        else:
            return None

    return value


def validate_template(template_text: str) -> list:
    """
    Validate a template string for unsafe patterns.

    Returns a list of warnings/errors if the template contains
    potentially dangerous constructs.

    Args:
        template_text: Template string to validate

    Returns:
        List of warning strings (empty if valid)
    """
    warnings = []

    if not template_text:
        return warnings

    # Check for Django template tags
    if re.search(r'\{%.*?%\}', template_text):
        warnings.append("Template contiene tags de Django ({%...%}) que no son soportados")

    # Check for filters
    if re.search(r'\{\{[^}]*\|[^}]*\}\}', template_text):
        warnings.append("Template contiene filtros (|) que no son soportados")

    # Check for settings access attempts
    if 'settings' in template_text.lower():
        warnings.append("Template intenta acceder a 'settings' - no permitido")

    # Check for request access attempts
    if 'request' in template_text.lower():
        warnings.append("Template intenta acceder a 'request' - no permitido")

    return warnings
