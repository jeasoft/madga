"""Tool registry + ToolContext + decorator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class ToolError(Exception):
    """Raised by tools when the call is invalid in a way the AI should
    learn from — e.g. missing required arg, post not found, no
    permission. The dispatcher turns this into a JSON-RPC error
    response with code -32602 (Invalid params) and the message.

    Distinct from unexpected exceptions, which become code -32603
    (Internal error) so an LLM can tell whether it can retry with
    different args or whether something is genuinely broken.
    """


@dataclass
class ToolContext:
    """Per-request context handed to every tool implementation.

    Bundles the authenticated user, their active Site, and the
    UserApiKey row used so audit / quota logic has everything in one
    place. ``site`` is None when the user has no Site memberships;
    tools that need it should raise ToolError early.
    """

    user: Any
    site: Any | None
    api_key: Any | None
    request: Any | None = None  # the HttpRequest, when called via HTTP


@dataclass
class Tool:
    """One registered tool the MCP server can dispatch to."""

    name: str
    description: str
    input_schema: dict
    handler: Callable
    requires_site: bool = True  # most tools need an active Site
    requires_permission: str = ""  # optional SiteUser permission name


_REGISTRY: dict[str, Tool] = {}


def register_tool(
    name: str,
    description: str,
    input_schema: dict | None = None,
    *,
    requires_site: bool = True,
    requires_permission: str = "",
):
    """Decorator: register a function as an MCP tool.

    ``input_schema`` follows MCP convention — a JSON Schema fragment
    describing the tool's arguments. Keep it small and well-described
    since the AI reads this to decide when/how to call the tool.
    """

    def deco(fn):
        if not name:
            raise ValueError("MCP tool needs a name")
        _REGISTRY[name] = Tool(
            name=name,
            description=description,
            input_schema=input_schema or {"type": "object", "properties": {}},
            handler=fn,
            requires_site=requires_site,
            requires_permission=requires_permission,
        )
        return fn

    return deco


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    return sorted(_REGISTRY.values(), key=lambda t: t.name)
