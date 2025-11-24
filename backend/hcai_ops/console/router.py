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
    events = store.all()
    recent = list(events[-50:])
    aggregator = MetricAggregator()
    metrics = aggregator.aggregate(events)

    total_events = len(events)
    sources = len({e.source_id for e in events})
    log_count = sum(1 for e in events if e.event_type == "log")
    metric_count = sum(1 for e in events if e.event_type == "metric")
    hb_count = sum(1 for e in events if e.event_type == "heartbeat")

    metric_rows = []
    for key, stats in metrics.items():
        metric_name, source_id = key.split(":")
        metric_rows.append(
            {
                "metric": metric_name,
                "source": source_id,
                "avg": round(stats.get("avg", 0), 2),
                "min": round(stats.get("min", 0), 2),
                "max": round(stats.get("max", 0), 2),
                "count": stats.get("count", 0),
            }
        )
    metric_rows = sorted(metric_rows, key=lambda r: r["metric"])

    recent_rows = []
    for e in reversed(recent):
        msg = e.log_message or e.metric_name or e.event_type
        recent_rows.append(
            {
                "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else e.timestamp,
                "source": e.source_id,
                "type": e.event_type,
                "level": (e.log_level or "").upper() if e.log_level else "",
                "message": msg,
            }
        )

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HCAI OPS Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0f172a;
      --card: #111827;
      --panel: rgba(255, 255, 255, 0.04);
      --border: rgba(255, 255, 255, 0.08);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #22d3ee;
      --red: #f43f5e;
      --amber: #fbbf24;
      --green: #34d399;
      --blue: #38bdf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 32px;
      font-family: "Manrope", "Segoe UI", sans-serif;
      background: radial-gradient(120% 120% at 10% 10%, rgba(34,211,238,0.12), transparent 45%), radial-gradient(120% 120% at 90% 20%, rgba(244,63,94,0.12), transparent 45%), var(--bg);
      color: var(--text);
    }}
    h1 {{ font-size: 28px; margin: 0 0 8px 0; }}
    h2 {{ font-size: 18px; margin: 0 0 12px 0; }}
    p {{ margin: 0; color: var(--muted); }}
    a.button {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: linear-gradient(135deg, var(--blue), var(--accent));
      color: #0b1222;
      font-weight: 700;
      border-radius: 10px;
      text-decoration: none;
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: 0 10px 30px rgba(56,189,248,0.25);
    }}
    .grid {{ display: grid; gap: 16px; }}
    .grid-4 {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.35);
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      backdrop-filter: blur(12px);
    }}
    .stat-value {{ font-size: 24px; font-weight: 700; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
    }}
    th {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; }}
    tr:hover td {{ background: rgba(255,255,255,0.03); }}
    .badge {{ padding: 6px 10px; border-radius: 10px; font-weight: 700; font-size: 12px; }}
    .badge.log {{ background: rgba(244,63,94,0.15); color: #fecdd3; border: 1px solid rgba(244,63,94,0.25); }}
    .badge.metric {{ background: rgba(34,211,238,0.12); color: #a5f3fc; border: 1px solid rgba(34,211,238,0.3); }}
    .badge.heartbeat {{ background: rgba(52,211,153,0.12); color: #bbf7d0; border: 1px solid rgba(52,211,153,0.3); }}
    .level {{
      padding: 4px 8px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 12px;
      border: 1px solid var(--border);
    }}
    .level.ERROR {{ background: rgba(244,63,94,0.18); color: #fecdd3; }}
    .level.WARNING {{ background: rgba(251,191,36,0.18); color: #fef3c7; }}
    .level.INFO {{ background: rgba(56,189,248,0.18); color: #bae6fd; }}
    .level.CRITICAL {{ background: rgba(248,113,113,0.2); color: #ffe4e6; }}
  </style>
</head>
<body>
  <div class="grid" style="gap:24px;">
    <div class="grid" style="gap:12px;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <div>
          <h1>HCAI OPS Console</h1>
          <p>Live operational view powered by the event store.</p>
        </div>
        <a class="button" href="/console/plan">Recompute control plan</a>
      </div>
      <div class="grid grid-4">
        <div class="card">
          <p class="pill">Events</p>
          <div class="stat-value">{total_events}</div>
          <p>Total ingested</p>
        </div>
        <div class="card">
          <p class="pill">Sources</p>
          <div class="stat-value">{sources}</div>
          <p>Unique agents/services</p>
        </div>
        <div class="card">
          <p class="pill">Logs</p>
          <div class="stat-value">{log_count}</div>
          <p>Log events</p>
        </div>
        <div class="card">
          <p class="pill">Metrics</p>
          <div class="stat-value">{metric_count}</div>
          <p>Metric samples</p>
        </div>
      </div>
      <div class="card">
        <h2>Metrics snapshot</h2>
        <table>
          <thead>
            <tr>
              <th>Metric</th><th>Source</th><th>Avg</th><th>Min</th><th>Max</th><th>Samples</th>
            </tr>
          </thead>
          <tbody>
            {''.join([f"<tr><td>{m['metric']}</td><td>{m['source']}</td><td>{m['avg']}</td><td>{m['min']}</td><td>{m['max']}</td><td>{m['count']}</td></tr>" for m in metric_rows]) or '<tr><td colspan=\"6\">No metrics yet</td></tr>'}
          </tbody>
        </table>
      </div>
      <div class="card">
        <h2>Recent events</h2>
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Type</th><th>Source</th><th>Level</th><th>Message</th></tr>
          </thead>
          <tbody>
            {''.join([f"<tr><td>{r['timestamp']}</td><td><span class='badge {r['type']}'>{r['type']}</span></td><td>{r['source']}</td><td><span class='level {r['level']}'>{r['level'] or '-'}</span></td><td>{r['message']}</td></tr>" for r in recent_rows]) or '<tr><td colspan=\"5\">No events yet</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)


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
