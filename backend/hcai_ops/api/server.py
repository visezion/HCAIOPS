from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from typing import Any

from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request
from fastapi.openapi.utils import get_openapi

from ..models.action_model import ActionRecommender
from ..models.alert_model import AlertImportanceModel
from ..models.risk_model import RiskModel
from . import routes_actions, routes_alerts, routes_risk
from hcai_ops.analytics.api import router as analytics_router
from hcai_ops.analytics.processors import MetricAggregator
from hcai_ops.intelligence.api import router as intelligence_router
from hcai_ops.control.api import router as control_router
from hcai_ops.console.router import router as console_router
from hcai_ops.api.ui_router import router as ui_router
from hcai_ops.config import HCAIConfig
from hcai_ops.config.env import get_settings
from hcai_ops.storage.filesystem import FileSystemStorage
from hcai_ops.analytics import event_store
from hcai_ops.agent.engine import AgentEngine
from hcai_ops.assets.asset_registry import AssetRegistry
from hcai_ops.assets.asset_model import Asset
from hcai_ops.assets.probes import run_asset_probe
from hcai_ops.assets.adapters import PingAdapter
from hcai_ops.agent_deploy.download_server import router as download_router
from hcai_ops.intelligence.agent import agent_check_in, record_update_status
from .swagger_custom import get_custom_swagger_ui_html, get_custom_redoc_html
from pydantic import BaseModel
import importlib.metadata
from hcai_ops.data.schemas import HCaiEvent

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = BASE_DIR / "web"
PROJECT_WEB_DIR = ROOT_DIR / "web"
MODEL_DIR = Path("models_store")

settings = get_settings()
app = FastAPI(
    title="HCAI OPS API",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
config = HCAIConfig()
storage = FileSystemStorage(settings.storage_dir)
setattr(event_store, "storage", storage)
agent = AgentEngine(event_store)
asset_registry = AssetRegistry(storage=None)


def _coerce_events(payload: Any) -> list[HCaiEvent]:
    """Normalize inbound payload into HCaiEvent list."""
    events: list[HCaiEvent] = []
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return events
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            ts = item.get("timestamp")
            if isinstance(ts, str):
                try:
                    item["timestamp"] = datetime.fromisoformat(ts)
                except Exception:
                    item["timestamp"] = datetime.utcnow()
            events.append(HCaiEvent(**item))
        except Exception:
            continue
    return events


@app.on_event("startup")
def load_models() -> None:
    """Load trained models from disk if available."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    risk_path = MODEL_DIR / "risk_model.pkl"
    alert_path = MODEL_DIR / "alert_model.pkl"
    action_path = MODEL_DIR / "action_model.pkl"

    if risk_path.exists():
        risk_model = RiskModel()
        risk_model.load(risk_path)
        routes_risk.risk_model = risk_model

    if alert_path.exists():
        alert_model = AlertImportanceModel()
        alert_model.load(alert_path)
        routes_alerts.alert_model = alert_model

    if action_path.exists():
        action_model = ActionRecommender()
        action_model.load(action_path)
        routes_actions.action_model = action_model


app.include_router(routes_risk.router)
app.include_router(routes_alerts.router)
app.include_router(routes_actions.router)
app.include_router(analytics_router)
app.include_router(intelligence_router)
app.include_router(control_router)
app.include_router(console_router)
app.include_router(ui_router)
app.include_router(download_router)
STATIC_DIR = BASE_DIR / "ui" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# Serve web assets (HTML/JS/CSS) for legacy UI pages
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")
agent_router = APIRouter(prefix="/agent", tags=["agent"])


@agent_router.get("/plan")
def agent_plan():
    return agent.build_plan()


@agent_router.post("/simulate")
def agent_sim(plan: dict):
    return agent.simulate_plan(plan)


@agent_router.post("/execute")
def agent_exec(plan: dict):
    return agent.execute_plan(plan)


@agent_router.get("/ping")
def agent_ping(version: str = "0.0.0"):
    return agent_check_in(version)


@app.get("/metrics/summary", tags=["analytics"])
def metrics_summary():
    """Lightweight summary for dashboards; returns zeros if no data."""
    aggregator = MetricAggregator()
    return aggregator.aggregate(event_store.all())


@app.get("/agents", tags=["agents"])
def list_agents():
    """Placeholder agents list until a registry is wired up."""
    return []


@app.get("/api/analytics/metrics/summary", tags=["analytics"])
def metrics_summary_api():
    return metrics_summary()


@app.get("/api/agents", tags=["agents"])
def list_agents_api():
    return list_agents()


@app.post("/events/ingest", tags=["events"])
@app.post("/api/events/ingest", tags=["events"])
def ingest_events(payload: dict | list[dict]):
    events = _coerce_events(payload)
    if events:
        event_store.add_events(events)
    return {"received": len(events)}


@app.get("/events/recent", tags=["events"])
@app.get("/api/events/recent", tags=["events"])
def recent_events(limit: int = 200):
    events = list(reversed(event_store.all()))[:limit]
    return [asdict(e) for e in events]


class AgentReport(BaseModel):
    system_metrics: dict | None = None
    network_metrics: dict | None = None
    process_metrics: dict | None = None
    service_status: dict | None = None
    recent_logs: list | None = None
    version: str = "0.0.0"


@agent_router.post("/report")
def agent_report(report: AgentReport):
    latest = agent_check_in(report.version)
    return latest


app.include_router(agent_router)

# Asset API
asset_api = APIRouter(prefix="/api/assets", tags=["assets"])


@asset_api.get("", response_model=list[Asset])
def list_assets():
    return asset_registry.list()


@asset_api.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: str):
    asset = asset_registry.get(asset_id)
    if not asset:
        return {}
    return asset


@asset_api.post("", response_model=Asset)
def register_asset(asset: Asset):
    asset_registry.register(asset)
    return asset


@asset_api.post("/{asset_id}/probe", response_model=Asset)
async def probe_asset(asset_id: str):
    asset = asset_registry.get(asset_id)
    if not asset:
        return {}
    updated = await run_asset_probe(asset, [PingAdapter()])
    asset_registry.register(updated)
    return updated


@asset_api.delete("/{asset_id}")
def remove_asset(asset_id: str):
    asset_registry.remove(asset_id)
    return {"status": "removed"}


app.include_router(asset_api)


class UpdateStatus(BaseModel):
    current_version: str
    update_result: str
    error_message: str | None = None


@app.post("/agent/update_status")
def agent_update_status(payload: UpdateStatus):
    record_update_status(payload.current_version, payload.update_result, payload.error_message)
    return {"status": "recorded"}


@app.get("/health")
async def health():
    return {"status": "ok"}


def override_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    version = importlib.metadata.version("hcai_ops") if "hcai_ops" in importlib.metadata.packages_distributions() else "0.0.0"
    openapi_schema = get_openapi(
        title="HCAI OPS Public API",
        version=version,
        description="API documentation for the Human-Centric AI Operations Platform",
        routes=app.routes,
        contact={"name": "HCAI OPS", "url": "https://hcaiops.ai"},
        license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    )
    openapi_schema["externalDocs"] = {"description": "Docs site", "url": "https://docs.hcaiops.ai"}
    openapi_schema["info"]["x-brand"] = {"logo": "/web/favicon.ico"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = override_openapi  # type: ignore


@app.get("/docs")
def custom_docs():
    return get_custom_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="HCAI OPS API Reference",
        swagger_favicon_url="/web/favicon.ico",
    )


@app.get("/redoc")
def custom_redoc():
    return get_custom_redoc_html(
        openapi_url=app.openapi_url,
        title="HCAI OPS API Reference",
        redoc_favicon_url="/web/favicon.ico",
    )

if PROJECT_WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=PROJECT_WEB_DIR), name="web")


@app.get("/")
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and (PROJECT_WEB_DIR / "index.html").exists():
        return FileResponse(PROJECT_WEB_DIR / "index.html")
    return {"status": "HCAI OPS API running"}
