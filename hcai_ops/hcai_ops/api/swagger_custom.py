from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html


def get_custom_swagger_ui_html(*, openapi_url: str, title: str, swagger_favicon_url: str):
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/custom.css",
        swagger_favicon_url=swagger_favicon_url,
    )


def get_custom_redoc_html(*, openapi_url: str, title: str, redoc_favicon_url: str):
    return get_redoc_html(
        openapi_url=openapi_url,
        title=title,
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        with_google_fonts=False,
        redoc_favicon_url=redoc_favicon_url,
    )
