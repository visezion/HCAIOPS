import time
from pathlib import Path

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse


def get_custom_swagger_ui_html(*, openapi_url: str, title: str, swagger_favicon_url: str):
    # Cache-bust custom assets and inline them so they always load (no CDN reliance).
    version = str(int(time.time()))
    html_response = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url=f"/static/swagger/custom.css?v={version}",
        swagger_favicon_url=swagger_favicon_url,
    )
    body = html_response.body.decode("utf-8") if isinstance(html_response.body, (bytes, bytearray)) else str(html_response.body)

    def _read_asset(name: str) -> str:
        path = Path(__file__).resolve().parent.parent / "ui" / "static" / "swagger" / name
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    custom_css = _read_asset("custom.css")
    custom_js = _read_asset("custom.js")

    if custom_css:
        body = body.replace("</head>", f"<style>{custom_css}</style></head>", 1)
    # Keep external link + inline JS to avoid caching issues.
    body += f'\n<script src="/static/swagger/custom.js?v={version}"></script>'
    if custom_js:
        body += f"\n<script>{custom_js}</script>"

    return HTMLResponse(content=body, status_code=html_response.status_code, headers={"Cache-Control": "no-store"})


def get_custom_redoc_html(*, openapi_url: str, title: str, redoc_favicon_url: str):
    return get_redoc_html(
        openapi_url=openapi_url,
        title=title,
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        with_google_fonts=False,
        redoc_favicon_url=redoc_favicon_url,
    )
