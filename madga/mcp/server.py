"""JSON-RPC 2.0 dispatcher for MCP requests.

Implements just the slice of MCP every client needs:

  - ``initialize``       — capabilities + server info
  - ``tools/list``       — list registered tools + their JSON schemas
  - ``tools/call``       — invoke one tool with args
  - ``ping``             — keepalive
  - ``notifications/initialized`` — silently accept

Anything else returns method-not-found (code -32601). Errors map to
JSON-RPC codes per spec: -32600 invalid request, -32601 method not
found, -32602 invalid params, -32603 internal error.
"""

from __future__ import annotations

import json
import logging
import traceback

from .registry import ToolError, all_tools, get_tool


logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "madga", "version": "0.4.0"}


def _err(id_, code: int, message: str, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def _ok(id_, result) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def dispatch(ctx, payload: dict) -> dict | None:
    """Handle one JSON-RPC request. Returns the response dict (or None
    for notifications, which don't expect a reply).
    """
    if not isinstance(payload, dict):
        return _err(None, -32600, "Request must be a JSON object")

    method = payload.get("method")
    req_id = payload.get("id")  # None for notifications
    params = payload.get("params") or {}

    # Notifications — accept silently
    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method == "ping":
        return _ok(req_id, {})

    if method == "tools/list":
        return _ok(req_id, {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema,
                }
                for t in all_tools()
            ],
        })

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        tool = get_tool(tool_name)
        if tool is None:
            return _err(req_id, -32601, f"Unknown tool: {tool_name}")

        if tool.requires_site and ctx.site is None:
            return _err(req_id, -32602,
                        "No active Site for this user. Call set_active_site or "
                        "ask the user to join a workspace.")

        try:
            result = tool.handler(ctx, **args)
        except ToolError as e:
            return _err(req_id, -32602, str(e))
        except TypeError as e:
            # Wrong arg shape — surface as invalid params
            return _err(req_id, -32602, f"Invalid arguments: {e}")
        except Exception as e:  # noqa: BLE001
            logger.exception("MCP tool %s crashed", tool_name)
            return _err(req_id, -32603, f"Internal error in tool '{tool_name}': {e}",
                        data={"trace": traceback.format_exc()[-800:]})

        # Wrap the tool's return into MCP content blocks.
        text = (
            result if isinstance(result, str)
            else json.dumps(result, default=str, ensure_ascii=False, indent=2)
        )
        return _ok(req_id, {"content": [{"type": "text", "text": text}]})

    return _err(req_id, -32601, f"Unknown method: {method}")
