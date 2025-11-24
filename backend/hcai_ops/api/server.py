import os
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any
import random
import subprocess
import sys
import joblib
import requests

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request
from fastapi.openapi.utils import get_openapi
from fastapi import Body

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
from . import routes_actions, routes_alerts, routes_risk
from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.intelligence.api import _compute_all, get_risk as intel_get_risk, get_incidents as intel_get_incidents, get_recommendations as intel_get_recommendations, get_overview as intel_get_overview
from hcai_ops.analytics.api import get_anomalies as analytics_get_anomalies, get_correlations as analytics_get_correlations, get_timeseries as analytics_get_timeseries
from hcai_ops.analytics.processors import LogAnomalyDetector
from hcai_ops.control.api import get_plan as control_get_plan, execute_control as control_execute, get_control_loop

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


def _iso(ts: datetime | None) -> str | None:
    if ts is None:
        return None
    if ts.tzinfo:
        return ts.astimezone(timezone.utc).isoformat()
    return ts.replace(tzinfo=timezone.utc).isoformat()


def _recent_logs(limit: int = 200) -> list[dict]:
    """Normalize recent log events for reuse across endpoints."""
    logs = [e for e in reversed(event_store.all()) if e.event_type == "log"][:limit]
    normalized = []
    for e in logs:
        payload = asdict(e)
        level = (payload.get("log_level") or "").strip()
        if not level:
            level = "INFO"
        payload["log_level"] = level.upper()
        payload["id"] = payload.get("id") or f"{payload.get('timestamp')}-{payload.get('source_id')}"
        msg = payload.get("log_message")
        payload["log_message"] = msg if isinstance(msg, str) else (str(msg) if msg is not None else "log event")
        ts = payload.get("timestamp")
        if hasattr(ts, "isoformat"):
            payload["timestamp"] = _iso(ts)
        normalized.append(payload)
    return normalized


def _build_alerts(limit: int = 50) -> list[dict[str, object]]:
    """Compose alert-like payloads for the legacy UI from incidents/anomalies/logs."""
    alerts: list[dict[str, object]] = []
    now_iso = datetime.utcnow().isoformat()

    for inc in intel_get_incidents() or []:
        alerts.append(
            {
                "alert_id": inc.get("incident_id") or f"incident-{len(alerts)}",
                "message": inc.get("summary") or "Incident detected",
                "source_id": inc.get("source_id") or "unknown",
                "severity": str(inc.get("severity") or "WARNING").upper(),
                "timestamp": inc.get("timestamp") or now_iso,
                "metadata": inc,
            }
        )
        if len(alerts) >= limit:
            break

    if len(alerts) < limit:
        try:
            anomalies = LogAnomalyDetector().detect(event_store.all()) or []
        except Exception:
            anomalies = []
        for idx, anomaly in enumerate(anomalies):
            alerts.append(
                {
                    "alert_id": anomaly.get("id") or anomaly.get("source_id") or f"anomaly-{idx}",
                    "message": f"Error spike: {anomaly.get('error_count', 0)} errors",
                    "source_id": anomaly.get("source_id") or "unknown",
                    "severity": "CRITICAL" if anomaly.get("anomaly") else "WARNING",
                    "timestamp": now_iso,
                    "metadata": anomaly,
                }
            )
            if len(alerts) >= limit:
                break

    if len(alerts) < limit:
        for log in _recent_logs(limit * 2):
            level = (log.get("log_level") or "INFO").upper()
            if level not in {"ERROR", "CRITICAL"}:
                continue
            alerts.append(
                {
                    "alert_id": log.get("id") or f"log-{len(alerts)}",
                    "message": log.get("log_message") or "log event",
                    "source_id": log.get("source_id") or "unknown",
                    "severity": "CRITICAL" if level == "CRITICAL" else "ERROR",
                    "timestamp": log.get("timestamp") or now_iso,
                    "metadata": log,
                }
            )
            if len(alerts) >= limit:
                break

    alerts.sort(key=lambda a: a.get("timestamp") or "", reverse=True)
    return alerts[:limit]


def _serialize_event_for_training(evt: HCaiEvent) -> dict[str, object]:
    data = asdict(evt)
    ts = data.get("timestamp")
    if hasattr(ts, "isoformat"):
        try:
            # Normalize to UTC and drop tzinfo to avoid pandas mixed tz errors.
            if ts.tzinfo:
                data["timestamp"] = ts.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
            else:
                data["timestamp"] = ts.isoformat()
        except Exception:
            data["timestamp"] = ts.isoformat()
    return data


def _seed_demo_events(sources: int = 3, windows: int = 24) -> list[HCaiEvent]:
    """Generate demo metrics/logs/alerts/incidents/actions for training."""
    base = datetime.utcnow() - timedelta(minutes=windows * 2)
    events: list[HCaiEvent] = []
    for idx in range(sources):
        source_id = f"demo-source-{idx+1}"
        incident_id = f"inc-{idx+1:03d}"
        alert_id = f"alert-{idx+1:03d}"
        for step in range(windows):
            ts = base + timedelta(minutes=step * 5)
            cpu = min(1.0, max(0.05, random.uniform(0.15, 0.95)))
            err_rate = min(1.0, max(0.0, cpu - 0.2 + random.uniform(-0.05, 0.1)))
            events.append(
                HCaiEvent(
                    timestamp=ts,
                    source_id=source_id,
                    event_type="metric",
                    metric_name="cpu",
                    metric_value=cpu,
                )
            )
            events.append(
                HCaiEvent(
                    timestamp=ts,
                    source_id=source_id,
                    event_type="metric",
                    metric_name="error_rate",
                    metric_value=err_rate,
                )
            )
            if err_rate > 0.5 and step % 4 == 0:
                events.append(
                    HCaiEvent(
                        timestamp=ts + timedelta(seconds=30),
                        source_id=source_id,
                        event_type="log",
                        log_message="Error spike detected",
                        log_level="ERROR",
                    )
                )
        # incident marking high risk
        events.append(
            HCaiEvent(
                timestamp=base + timedelta(minutes=windows * 5 + 1),
                source_id=source_id,
                event_type="incident",
                incident_label="high_error_rate",
                recommended_action="restart_service",
                outcome_label="open",
            )
        )
        # alert tied to action
        events.append(
            HCaiEvent(
                timestamp=base + timedelta(minutes=windows * 5 + 2),
                source_id=source_id,
                event_type="alert",
                alert_id=alert_id,
                metric_value=0.8,
                extras={"severity": 0.9},
            )
        )
        # action taken
        events.append(
            HCaiEvent(
                timestamp=base + timedelta(minutes=windows * 5 + 3),
                source_id=source_id,
                event_type="operator_action",
                alert_id=alert_id,
                applied_action="restart_service",
                op_action_type="restart_service",
                outcome_label="resolved",
            )
        )
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
feedback_stream = "feedback"
cooling_state: dict[str, object] = {
    "mode": "auto",
    "fan_speed": 50,
    "target_temp": 22,
    "updated_at": datetime.utcnow().isoformat(),
}


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


def _restart_hook(agent_id: str) -> dict:
    """Optional external orchestration hook for agent restarts."""
    hook = os.getenv("AGENT_RESTART_WEBHOOK", "").strip()
    if not hook:
        return {"called": False, "message": "No AGENT_RESTART_WEBHOOK set"}
    try:
        resp = requests.post(hook, json={"agent_id": agent_id}, timeout=5)
        return {"called": True, "status_code": resp.status_code, "response": resp.text[:500]}
    except Exception as exc:  # pragma: no cover
        return {"called": True, "error": str(exc)}


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
        ts = event.timestamp
        if ts is not None:
            agents[src]["last_seen"] = ts if agents[src]["last_seen"] is None else max(agents[src]["last_seen"], ts)
    for src, info in agents.items():
        last_seen = info["last_seen"]
        if last_seen is None:
            info["status"] = "unknown"
        else:
            # normalize to naive for diff
            if last_seen.tzinfo:
                last_seen = last_seen.astimezone(timezone.utc).replace(tzinfo=None)
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


@app.get("/api/ingest/status", tags=["events"])
def ingest_status():
    stats = {}
    if hasattr(event_store, "stats"):
        try:
            stats = event_store.stats()
        except Exception:
            stats = {}
    return {
        "status": "ok",
        "stats": stats,
        "stored_events": len(event_store.all()),
    }


@app.get("/events/recent", tags=["events"])
@app.get("/api/events/recent", tags=["events"])
def recent_events(limit: int = 200):
    # Pagination support
    limit = max(1, min(limit, 1000))
    events = list(reversed(event_store.all()))
    return [asdict(e) for e in events[:limit]]


@app.get("/logs/recent", tags=["events"])
@app.get("/api/logs/recent", tags=["events"])
def recent_logs(limit: int = 200):
    """Return recent log events only."""
    limit = max(1, min(limit, 1000))
    return _recent_logs(limit)


@app.get("/alerts/recent", tags=["alerts"])
@app.get("/api/alerts/recent", tags=["alerts"])
def recent_alerts(limit: int = 50):
    """Expose alerts for the legacy UI, driven by incidents/anomalies/logs."""
    return _build_alerts(limit)


@app.post("/api/models/train_all", tags=["models"])
def train_all_models():
    """Train risk, alert, and action models from current in-memory events."""
    events = event_store.all()
    if not events:
        return {"status": "error", "message": "No events available to train. Ingest data first."}

    payload = [_serialize_event_for_training(e) for e in events]
    results: dict[str, object] = {"events_used": len(payload), "saved_to": "models_store"}

    # Risk model
    if routes_risk.risk_model is None:
        routes_risk.risk_model = RiskModel()
    try:
        metrics = routes_risk.risk_model.fit_from_events(routes_risk._dicts_to_events(payload))
        routes_risk.risk_model.save(MODEL_DIR / "risk_model.pkl")
        results["risk"] = metrics
    except Exception as exc:  # pragma: no cover
        results["risk_error"] = str(exc)

    # Alert model
    if routes_alerts.alert_model is None:
        routes_alerts.alert_model = AlertImportanceModel()
    try:
        metrics = routes_alerts.alert_model.fit_from_events(routes_alerts._dicts_to_events(payload))
        routes_alerts.alert_model.save(MODEL_DIR / "alert_model.pkl")
        results["alerts"] = metrics
    except Exception as exc:  # pragma: no cover
        results["alerts_error"] = str(exc)

    # Action recommender
    if routes_actions.action_model is None:
        routes_actions.action_model = ActionRecommender()
    try:
        routes_actions.action_model.fit_from_events(routes_actions._dicts_to_events(payload))
        routes_actions.action_model.save(MODEL_DIR / "action_model.pkl")
        rows = 0
        if routes_actions.action_model.action_history is not None:
            rows = len(routes_actions.action_model.action_history)
        results["actions"] = {"status": "trained", "rows": rows}
    except Exception as exc:  # pragma: no cover
        results["actions_error"] = str(exc)

    results["status"] = "ok" if not any(k.endswith("_error") for k in results) else "partial"
    return results


class ExcelTrainRequest(BaseModel):
    input: str
    target: str
    sheet: str | None = None
    model_out: str | None = None
    test_size: float | None = None
    sample_rows: int | None = None
    drop_cols: str | None = None
    drop_patterns: str | None = None
    time_split_col: str | None = None
    time_split_ratio: float | None = None
    class_weight: str | None = None


@app.post("/api/models/train_excel", tags=["models"])
def train_excel(req: ExcelTrainRequest):
    """Run the Excel training helper script."""
    allowed_roots = {ROOT_DIR.resolve(), ROOT_DIR.parent.resolve()}

    # Resolve input (try backend/ and repo root).
    candidates = []
    raw_input = Path(req.input)
    if raw_input.is_absolute():
        candidates.append(raw_input)
    else:
        candidates.append((ROOT_DIR / raw_input).resolve())
        candidates.append((ROOT_DIR.parent / raw_input).resolve())

    input_path = next((p for p in candidates if p.exists()), None)
    if input_path is None:
        return {"status": "error", "message": f"Input not found. Tried: {', '.join(str(p) for p in candidates)}"}
    if not any(str(input_path).startswith(str(root)) for root in allowed_roots):
        return {"status": "error", "message": "Input path must be inside the project directory."}

    model_out = Path(req.model_out) if req.model_out else MODEL_DIR / "excel_model.pkl"
    if not model_out.is_absolute():
        # Save alongside backend or repo root
        model_out = (ROOT_DIR.parent / model_out).resolve()
    if not any(str(model_out).startswith(str(root)) for root in allowed_roots):
        return {"status": "error", "message": "Output path must be inside the project directory."}
    model_out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "train_from_excel.py"),
        "--input",
        str(input_path),
        "--target",
        req.target,
        "--model-out",
        str(model_out),
    ]
    if req.sheet:
        cmd.extend(["--sheet", req.sheet])
    if req.test_size:
        cmd.extend(["--test-size", str(req.test_size)])
    if req.sample_rows:
        cmd.extend(["--sample-rows", str(req.sample_rows)])
    if req.drop_cols:
        cmd.extend(["--drop-cols", req.drop_cols])
    if req.drop_patterns:
        cmd.extend(["--drop-patterns", req.drop_patterns])
    if req.time_split_col:
        cmd.extend(["--time-split-col", req.time_split_col])
    if req.time_split_ratio:
        cmd.extend(["--time-split-ratio", str(req.time_split_ratio)])
    if req.class_weight:
        cmd.extend(["--class-weight", req.class_weight])

    result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
    status = "ok" if result.returncode == 0 else "error"
    stdout_lines = result.stdout.splitlines()
    stderr_lines = result.stderr.splitlines()
    return {
        "status": status,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "stdout_lines": stdout_lines,
        "stderr_lines": stderr_lines,
        "model_out": str(model_out),
        "input": str(input_path),
    }


class ExcelPredictRequest(BaseModel):
    items: list[dict]
    threshold: float | None = None


def _load_excel_model(path: Path) -> tuple[object, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Model not found at {path}")
    obj = joblib.load(path)
    if isinstance(obj, dict) and "model" in obj and "features" in obj:
        return obj["model"], obj["features"]
    # Fallback: assume obj is model and no features list
    raise ValueError("Model file missing required structure {'model': ..., 'features': [...]} ")


@app.get("/api/models/excel_features", tags=["models"])
def excel_features():
    """Return feature order for the saved Excel/CSV model."""
    model_path = MODEL_DIR / "excel_model.pkl"
    try:
        _, features = _load_excel_model(model_path)
        return {"status": "ok", "features": features, "model_path": str(model_path)}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "model_path": str(model_path)}


@app.post("/api/models/predict_excel", tags=["models"])
def predict_excel(req: ExcelPredictRequest):
    """Predict using the latest excel_model.pkl on feature-aligned payloads."""
    model_path = MODEL_DIR / "excel_model.pkl"
    try:
        model, feature_order = _load_excel_model(model_path)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    preds = []
    for item in req.items:
        row = []
        for feat in feature_order:
            val = item.get(feat, 0)
            try:
                row.append(float(val))
            except Exception:
                row.append(0.0)
        preds.append(row)

    import numpy as np

    X = np.array(preds)
    out = {}
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        out["proba"] = proba[:, 1].tolist()
        if req.threshold is not None:
            labels = (proba[:, 1] >= req.threshold).astype(int).tolist()
        else:
            labels = model.predict(X).tolist()
        out["pred"] = labels
    else:
        labels = model.predict(X).tolist()
        out["pred"] = labels

    return {
        "status": "ok",
        "count": len(preds),
        "model_path": str(model_path),
        "features": feature_order,
        "results": out,
    }


@app.post("/api/events/seed_demo", tags=["models"])
def seed_demo_events(count: int = 3, windows: int = 24):
    """Populate the in-memory store with demo events for training and UI."""
    demo_events = _seed_demo_events(sources=max(1, count), windows=max(6, windows))
    event_store.add_events(demo_events)
    return {"status": "ok", "added": len(demo_events), "sources": count, "windows": windows}


@app.post("/agents/{agent_id}/restart", tags=["agents"])
@app.post("/api/agents/{agent_id}/restart", tags=["agents"])
def restart_agent(agent_id: str):
    """
    Restart endpoint with optional external orchestration hook (AGENT_RESTART_WEBHOOK).
    """
    hook_result = _restart_hook(agent_id)
    return {"status": "accepted", "agent_id": agent_id, "hook": hook_result}


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
    return analytics_get_anomalies(store=event_store)


@app.get("/api/analytics/correlations", tags=["analytics"])
def analytics_correlations_api():
    return analytics_get_correlations(store=event_store)


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
    return control_get_plan(loop=get_control_loop())


@app.post("/api/control/execute", tags=["control"])
def control_execute_api(payload: dict | None = None):
    return control_execute(payload or {}, loop=get_control_loop())


@app.post("/api/control/cooling", tags=["control"])
def control_cooling(payload: dict | None = None):
    """Accept cooling/thermostat settings from UI and log them for observability."""
    data = payload or {}
    for key in ("mode", "fan_speed", "target_temp"):
        if key in data:
            cooling_state[key] = data[key]
    cooling_state["updated_at"] = datetime.utcnow().isoformat()
    evt = HCaiEvent(
        timestamp=datetime.utcnow(),
        source_id="controller",
        event_type="control_action",
        log_message="Updated cooling settings",
        log_level="INFO",
        extras={"cooling_state": dict(cooling_state)},
    )
    event_store.add_events([evt])
    return {"status": "ok", "message": "Cooling settings applied.", "state": cooling_state}


@app.post("/api/agent/run", tags=["agent"])
def agent_run(payload: dict | None = None):
    """Trigger a lightweight plan build/simulation and echo the result."""
    command = (payload or {}).get("command")
    plan = agent.build_plan().get("plan", {})
    simulation = agent.simulate_plan(plan)
    event_store.add_events(
        [
            HCaiEvent(
                timestamp=datetime.utcnow(),
                source_id="agent",
                event_type="agent_run",
                log_message=command or "run_plan",
                log_level="INFO",
                extras={"plan": plan, "simulation": simulation},
            )
        ]
    )
    summary = f"Ran agent plan {command or ''}".strip()
    return {"summary": summary or "Ran agent plan", "plan": plan, "simulation": simulation}


class AgentReport(BaseModel):
    system_metrics: dict | None = None
    network_metrics: dict | None = None
    process_metrics: dict | None = None
    service_status: dict | None = None
    recent_logs: list | None = None
    version: str = "0.0.0"


@agent_router.post("/report")
def agent_report(report: AgentReport):
    """Store agent telemetry (metrics/logs) and respond with update status."""
    latest = agent_check_in(report.version)
    now = datetime.utcnow()
    events: list[HCaiEvent] = []

    def push_metric(name: str, value: object):
        try:
            val = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return
        # Normalize to 0-1 range when obvious percentages arrive.
        if val > 1:
            val = round(val / 100, 4)
        events.append(
            HCaiEvent(
                timestamp=now,
                source_id="agent",
                event_type="metric",
                metric_name=name,
                metric_value=val,
            )
        )

    for key, block in (
        ("system", report.system_metrics),
        ("network", report.network_metrics),
    ):
        if isinstance(block, dict):
            for metric_name, metric_value in block.items():
                push_metric(f"{key}.{metric_name}", metric_value)

    if isinstance(report.process_metrics, dict):
        for proc_name, metrics in report.process_metrics.items():
            if isinstance(metrics, dict):
                for metric_name, metric_value in metrics.items():
                    push_metric(f"process.{proc_name}.{metric_name}", metric_value)
            else:
                push_metric(f"process.{proc_name}", metrics)

    if isinstance(report.service_status, dict):
        for service, status in report.service_status.items():
            events.append(
                HCaiEvent(
                    timestamp=now,
                    source_id="agent",
                    event_type="service_status",
                    log_message=status,
                    log_level="INFO",
                    extras={"service": service},
                )
            )

    if isinstance(report.recent_logs, list):
        for item in report.recent_logs:
            if isinstance(item, dict):
                msg = item.get("message") or item.get("log_message") or str(item)
                level = (item.get("level") or item.get("log_level") or "INFO").upper()
                extras = {k: v for k, v in item.items() if k not in {"message", "log_message", "level", "log_level"}}
            else:
                msg = str(item)
                level = "INFO"
                extras = {}
            events.append(
                HCaiEvent(
                    timestamp=now,
                    source_id="agent",
                    event_type="log",
                    log_message=msg,
                    log_level=level,
                    extras=extras,
                )
            )

    if events:
        event_store.add_events(events)

    return {"status": "recorded", "ingested_events": len(events), "latest": latest}


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


class FeedbackPayload(BaseModel):
    incident_id: str
    source_id: str | None = None
    accepted: bool | None = None  # did operator accept the plan?
    correct: bool | None = None  # was the AI decision correct?
    action: str | None = None  # action taken/approved
    notes: str | None = None
    severity: str | None = None
    recommended_action: str | None = None
    risk: float | None = None
    created_at: datetime = datetime.utcnow()


@app.post("/api/feedback", tags=["feedback"])
def submit_feedback(payload: FeedbackPayload = Body(...)):
    """Capture human-in-the-loop validation for AI plans."""
    record = payload.model_dump()
    storage.append(feedback_stream, record)
    return {"status": "recorded", "feedback": record}


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
    docs_path = PROJECT_WEB_DIR / "docs.html"
    if docs_path.exists():
        return FileResponse(docs_path)
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
