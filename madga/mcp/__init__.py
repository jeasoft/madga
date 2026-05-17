"""MCP server for MADGA — expose the studio's core operations as
Model Context Protocol tools so AI assistants (Claude, Claude Code,
custom agents) can drive MADGA programmatically.

Transport: HTTP at ``/mcp/`` (POST JSON-RPC requests).
Auth: ``Authorization: Bearer madga_<UserApiKey>`` — the same per-user
keys used by the headless API.
Isolation: every tool scopes its queries by the authenticated user's
active Site (first active membership; multi-site users get a
``set_active_site`` tool to switch).

Built-in tools (kept intentionally small; host projects can register
more via ``madga.mcp.register_tool``):

  - **Sites**: list_sites, set_active_site
  - **Content**: list_posts, get_post, create_post, update_post,
                 publish_post, list_pages
  - **Audience**: list_subscribers, list_form_submissions
  - **Channels**: list_channels, list_broadcasts, broadcast

Roll-your-own JSON-RPC implementation — the spec is small enough that
adding the official ``mcp`` SDK (async, anyio-based) just to get
``initialize`` / ``tools/list`` / ``tools/call`` would force us to
push every Django view through ASGI. Sync Django suits MADGA's stack.
"""

from .registry import (
    Tool,
    ToolContext,
    ToolError,
    all_tools,
    get_tool,
    register_tool,
)

# Side-effect: load and register every built-in tool.
from . import tools  # noqa: F401

__all__ = [
    "Tool",
    "ToolContext",
    "ToolError",
    "all_tools",
    "get_tool",
    "register_tool",
]
