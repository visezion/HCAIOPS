import os
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
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
from hcai_ops.intelligence.api import _compute_all, get_risk as intel_get_risk, get_incidents as intel_get_incidents, get_recommendations as intel_get_recommendations, get_overview as intel_get_overview
from hcai_ops.analytics.api import get_anomalies as analytics_get_anomalies, get_correlations as analytics_get_correlations, get_timeseries as analytics_get_timeseries
from hcai_ops.control.api import get_plan as control_get_plan, execute_control as control_execute

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
cors_env = os.getenv("HCAI_CORS_ORIGINS", "")
cors_overrides = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
allowed_origins = list(
    {
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://hcaiops.vicezion.com",
        "http://hcaiops.vicezion.com",
        *cors_overrides,
    }
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Lightweight summary for dashboards; returns list with history and stats."""
    aggregator = MetricAggregator()
    events = event_store.all()
    summary = aggregator.aggregate(events)

    history: dict[str, list[dict[str, object]]] = {}
    # keep the 10 most recent samples per metric/source
    for event in reversed(events):
        if event.metric_name is None or event.metric_value is None:
            continue
        key = f"{event.metric_name}:{event.source_id}"
        bucket = history.setdefault(key, [])
        if len(bucket) >= 10:
            continue
        bucket.append(
            {
                "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else None,
                "value": event.metric_value,
            }
        )

    results: list[dict[str, object]] = []
    for key, stats in summary.items():
        metric_name, source_id = key.split(":", 1)
        results.append(
            {
                "metric_name": metric_name,
                "source_id": source_id,
                "metric_value": stats.get("avg"),
                "min": stats.get("min"),
                "max": stats.get("max"),
                "count": stats.get("count"),
                "history": list(reversed(history.get(key, []))),
            }
        )
    return results


@app.get("/agents", tags=["agents"])
def list_agents():
    """Derive agents from recent heartbeats/metrics in the in-memory store."""
    agents: dict[str, dict[str, Any]] = {}
    now = datetime.utcnow().replace(tzinfo=None)
    for event in event_store.all():
        src = event.source_id
        agents.setdefault(
            src,
            {
                "id": src,
                "name": src,
                "last_seen": None,
                "status": "unknown",
                "latency": None,
            },
        )
        agents[src]["last_seen"] = event.timestamp
    for src, info in agents.items():
        last_seen = info["last_seen"]
        if last_seen is None:
            info["status"] = "unknown"
        else:
            # normalize to naive for diff
            if last_seen.tzinfo:
                last_seen = last_seen.replace(tzinfo=None)
            delta = (now - last_seen).total_seconds()
            if delta <= 60:
                info["status"] = "healthy"
            elif delta <= 180:
                info["status"] = "degraded"
            else:
                info["status"] = "offline"
            info["latency"] = delta
    return list(agents.values())


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


@app.get("/logs/recent", tags=["events"])
@app.get("/api/logs/recent", tags=["events"])
def recent_logs(limit: int = 200):
    """Return recent log events only."""
    logs = [e for e in reversed(event_store.all()) if e.event_type == "log"][:limit]
    normalized = []
    for e in logs:
        payload = asdict(e)
        level = (payload.get("log_level") or "").strip()
        if not level:
            level = "INFO"
        payload["log_level"] = level.upper()
        payload["id"] = payload.get("id") or f"{payload.get('timestamp')}-{payload.get('source_id')}"
        # Ensure message and timestamp are display-friendly
        msg = payload.get("log_message")
        payload["log_message"] = msg if isinstance(msg, str) else (str(msg) if msg is not None else "log event")
        ts = payload.get("timestamp")
        if hasattr(ts, "isoformat"):
            payload["timestamp"] = ts.isoformat()
        normalized.append(payload)
    return normalized


@app.post("/agents/{agent_id}/restart", tags=["agents"])
@app.post("/api/agents/{agent_id}/restart", tags=["agents"])
def restart_agent(agent_id: str):
    """
    Placeholder restart endpoint; in real deployments trigger a service restart.
    """
    # TODO: integrate with actual agent orchestration/service manager
    return {"status": "accepted", "agent_id": agent_id, "message": "Restart requested (stub)." }


@app.get("/api/intelligence/insights", tags=["intelligence"])
def intelligence_insights():
    """Map dashboard JS expectation to intelligence overview."""
    data = _compute_all()
    incidents = data.get("incidents") or []
    risk = data.get("risk") or {}
    recommendations = data.get("recommendations") or []
    return {"incidents": incidents, "risk": risk, "recommendations": recommendations}


@app.get("/analytics/summary", tags=["analytics"])
def analytics_summary_alias():
    """Alias for SPA endpoints without /api prefix."""
    return metrics_summary()


@app.get("/analytics/timeseries", tags=["analytics"])
def analytics_timeseries_alias(minutes: int = 180):
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    events = event_store.since(cutoff)
    return [asdict(e) for e in events]


@app.get("/ingest/events", tags=["events"])
def ingest_events_alias(limit: int = 0):
    """Alias to satisfy SPA ingest helper; returns recent events."""
    return recent_events(limit or 200)


# API-prefixed mirrors for SPA calls
@app.get("/api/analytics/anomalies", tags=["analytics"])
def analytics_anomalies_api():
    return analytics_get_anomalies()


@app.get("/api/analytics/correlations", tags=["analytics"])
def analytics_correlations_api():
    return analytics_get_correlations()


@app.get("/api/analytics/timeseries", tags=["analytics"])
def analytics_timeseries_api(minutes: int = 180):
    return analytics_timeseries_alias(minutes)


@app.get("/api/intelligence/overview", tags=["intelligence"])
def intelligence_overview_api():
    return intel_get_overview()


@app.get("/api/intelligence/risk", tags=["intelligence"])
def intelligence_risk_api():
    return intel_get_risk()


@app.get("/api/intelligence/incidents", tags=["intelligence"])
def intelligence_incidents_api():
    return intel_get_incidents()


@app.get("/api/intelligence/recommendations", tags=["intelligence"])
def intelligence_recommendations_api():
    return intel_get_recommendations()


@app.get("/api/control/plan", tags=["control"])
def control_plan_api():
    return control_get_plan()


@app.post("/api/control/execute", tags=["control"])
def control_execute_api(payload: dict | None = None):
    return control_execute(payload or {})


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
