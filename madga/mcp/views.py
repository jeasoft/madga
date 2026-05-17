"""Django view that exposes the MCP server over HTTP at ``/mcp/``."""

from __future__ import annotations

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .auth import authenticate
from .registry import ToolContext
from .server import dispatch


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class MCPView(View):
    """POST JSON-RPC requests here. Auth: Bearer madga_<key>.

    A GET on this URL returns a tiny capability summary so devs can
    sanity-check the endpoint is mounted (any browser hit gets a clear
    JSON, never an HTML 405 page).
    """

    def get(self, request):
        from madga.mcp.registry import all_tools
        return JsonResponse({
            "service": "madga.mcp",
            "tools": len(all_tools()),
            "transport": "http-jsonrpc",
            "auth": "Authorization: Bearer madga_<UserApiKey>",
            "doc": "POST a JSON-RPC 2.0 request (initialize, tools/list, tools/call).",
        })

    def post(self, request):
        auth_result = authenticate(request)
        if auth_result is None:
            return JsonResponse(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32001, "message": "Missing or invalid Bearer token"}},
                status=401,
            )
        user, api_key, site = auth_result

        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError as e:
            return JsonResponse(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": f"Parse error: {e}"}},
                status=400,
            )

        ctx = ToolContext(user=user, site=site, api_key=api_key, request=request)

        # JSON-RPC supports batches (list of requests). Handle both.
        if isinstance(payload, list):
            responses = []
            for item in payload:
                r = dispatch(ctx, item)
                if r is not None:
                    responses.append(r)
            if not responses:
                return HttpResponse(status=204)  # all notifications
            return JsonResponse(responses, safe=False)

        response = dispatch(ctx, payload)
        if response is None:
            return HttpResponse(status=204)  # notification
        return JsonResponse(response)
