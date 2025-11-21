from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
import click

from hcai_ops.analytics import event_store
from hcai_ops.control.loops import ControlLoop
from hcai_ops.analytics.processors import MetricAggregator
from hcai_ops.intelligence.risk import RiskScoringEngine
from hcai_ops.intelligence.incidents import IncidentEngine
from hcai_ops.intelligence.recommendations import RecommendationEngine
from hcai_ops.control.policies import PolicyEngine

router = APIRouter(prefix="/console", tags=["console"])


def get_event_store():
    return event_store


@router.get("/", response_class=HTMLResponse)
def dashboard(store=Depends(get_event_store)):
    events = store.all()[-20:]
    html = "<html><body><h2>HCAI Console</h2>"
    html += "<h3>Recent Events</h3><ul>"
    for e in events:
        html += f"<li>{e.timestamp} - {e.source_id} - {e.event_type}</li>"
    html += "</ul>"
    html += "<a href='/console/plan'>Recompute Control Plan</a>"
    html += "</body></html>"
    return html


@router.get("/plan")
def view_plan(store=Depends(get_event_store)):
    loop = ControlLoop(
        store,
        RiskScoringEngine(),
        IncidentEngine(),
        RecommendationEngine(),
        PolicyEngine(),
    )
    return loop.build_plan()


@click.command("start-agent")
def start_agent():
    """Start the HCAI OPS local agent."""
    from hcai_ops_agent.main import run

    run()
