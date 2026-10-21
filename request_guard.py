"""Request guard shared by the Ultra Tools HTTP routes.

Some Ultra Tools routes act on the local disk or on saved settings: they browse
folders, register external image folders, delete input images, list wildcard
folders and save the translation API key.  A browser sends requests to
127.0.0.1 from any web page the user happens to have open, so these routes must
only act on requests made by the ComfyUI page itself.

Two checks are used:

* Cross-site requests are refused (``Sec-Fetch-Site: cross-site``).  ComfyUI's
  own origin middleware already does this, but it is switched off when ComfyUI
  runs with ``--enable-cors-header``, so the routes check it themselves too.
* Routes that change state, browse the disk or read a path supplied by the
  caller also require a per-process token.  The token is created when ComfyUI
  starts, is only handed out to same-origin requests, and the Ultra Tools
  frontend sends it back in the ``X-Ultra-Tools-Token`` header (or the
  ``ut_token`` query parameter for <img> URLs, which cannot carry headers).

Nothing here changes what a permitted request does.
"""

import hmac
import secrets
from urllib.parse import urlsplit

TOKEN_HEADER = "X-Ultra-Tools-Token"
TOKEN_QUERY = "ut_token"
TOKEN_ROUTE = "/ultra_tools/security/token"
ERROR_CODE = "ultra_tools_token"

_SERVER_TOKEN_ATTR = "_ultra_tools_security_token_v1"
_ROUTE_MARKER = "_ultra_tools_security_token_route_v1"
_MODULE_TOKEN = secrets.token_urlsafe(32)

_REJECT_MESSAGE = (
    "보안 확인에 실패했습니다. ComfyUI 화면을 새로고침(F5)한 뒤 다시 시도해 주세요. "
    "(Ultra Tools security check failed. Please reload the ComfyUI page.)"
)


def _prompt_server():
    try:
        from server import PromptServer  # type: ignore

        return PromptServer.instance
    except Exception:
        return None


def current_token():
    """The token of this ComfyUI process.

    It is kept on the PromptServer instance so that every module of the pack
    shares one value, even if this file were ever imported twice under
    different module names.
    """
    server = _prompt_server()
    if server is None:
        return _MODULE_TOKEN
    token = getattr(server, _SERVER_TOKEN_ATTR, None)
    if not token:
        token = _MODULE_TOKEN
        try:
            setattr(server, _SERVER_TOKEN_ATTR, token)
        except Exception:
            pass
    return str(token)


def _header(request, name):
    try:
        return str(request.headers.get(name, "") or "")
    except Exception:
        return ""


def is_cross_site(request, strict=False):
    """True when the request clearly did not come from the ComfyUI page.

    The default check matches ComfyUI's own middleware.  ``strict`` (used only
    by the token route) also refuses same-site pages, ``Origin: null`` and an
    Origin whose host differs from the Host header.
    """
    site = _header(request, "Sec-Fetch-Site").strip().lower()
    if site == "cross-site":
        return True
    if not strict:
        return False
    if site == "same-site":
        return True
    origin = _header(request, "Origin").strip()
    if not origin:
        return False
    if origin.lower() == "null":
        return True
    host = _header(request, "Host").strip().lower()
    try:
        origin_host = urlsplit(origin).netloc.lower()
    except ValueError:
        return True
    return bool(host and origin_host and origin_host != host)


def has_valid_token(request):
    supplied = _header(request, TOKEN_HEADER).strip()
    if not supplied:
        try:
            supplied = str(request.rel_url.query.get(TOKEN_QUERY, "") or "").strip()
        except Exception:
            supplied = ""
    if not supplied:
        return False
    return hmac.compare_digest(supplied.encode("utf-8"), current_token().encode("utf-8"))


def reject_response(web):
    return web.json_response(
        {"ok": False, "error": _REJECT_MESSAGE, "type": "security", "code": ERROR_CODE},
        status=403,
        headers={"Cache-Control": "no-store"},
    )


def guard_request(request, web, require_token=True):
    """Return None when the request may proceed, otherwise a 403 response."""
    if is_cross_site(request):
        return reject_response(web)
    if require_token and not has_valid_token(request):
        return reject_response(web)
    return None


def register_token_route():
    """Register GET /ultra_tools/security/token once per ComfyUI process."""
    try:
        from aiohttp import web  # type: ignore
    except Exception:
        return False
    server = _prompt_server()
    if server is None:
        return False
    if getattr(server, _ROUTE_MARKER, False):
        return True
    try:
        routes = server.routes
    except Exception:
        return False

    @routes.get(TOKEN_ROUTE)
    async def _ultra_tools_token_route(request):
        if is_cross_site(request, strict=True):
            return reject_response(web)
        return web.json_response(
            {"ok": True, "token": current_token(), "header": TOKEN_HEADER, "query": TOKEN_QUERY},
            headers={"Cache-Control": "no-store"},
        )

    try:
        setattr(server, _ROUTE_MARKER, True)
    except Exception:
        pass
    return True
