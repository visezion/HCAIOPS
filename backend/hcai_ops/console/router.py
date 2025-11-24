from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from hcai_ops.analytics import event_store
from hcai_ops.analytics.processors import MetricAggregator

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
    log_events = [e for e in events if e.event_type == "log"]
    log_count = len(log_events)
    level_counts = {
        "CRITICAL": sum(1 for e in log_events if (e.log_level or "").upper() == "CRITICAL"),
        "ERROR": sum(1 for e in log_events if (e.log_level or "").upper() == "ERROR"),
        "WARNING": sum(1 for e in log_events if (e.log_level or "").upper() == "WARNING"),
        "INFO": sum(1 for e in log_events if (e.log_level or "").upper() == "INFO"),
    }
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

    error_rows = []
    for e in reversed(log_events):
        lvl = (e.log_level or "").upper()
        if lvl in {"ERROR", "CRITICAL"}:
            error_rows.append(
                {
                    "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else e.timestamp,
                    "source": e.source_id,
                    "level": lvl,
                    "message": e.log_message or e.metric_name or e.event_type,
                }
            )
    error_rows = error_rows[:30]

    metric_table = "".join(
        [
            "<tr><td>{metric}</td><td>{source}</td><td>{avg}</td><td>{min}</td><td>{max}</td><td>{count}</td></tr>".format(
                **m
            )
            for m in metric_rows
        ]
    ) or "<tr><td colspan='6' style='text-align:center;color:#94a3b8;padding:12px;'>No metrics yet.</td></tr>"

    events_table = "".join(
        [
            "<tr><td>{timestamp}</td><td>{source}</td><td>{type}</td><td>{level}</td><td>{message}</td></tr>".format(
                **r
            )
            for r in recent_rows
        ]
    ) or "<tr><td colspan='5' style='text-align:center;color:#94a3b8;padding:12px;'>No events yet.</td></tr>"

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
      --amber: #f59e0b;
      --green: #10b981;
      --shadow: 0 16px 60px rgba(0,0,0,0.3);
    }}
    body {{
      margin: 0;
      background: #0b1224;
      color: var(--text);
      font-family: 'Manrope', system-ui, -apple-system, sans-serif;
    }}
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      box-shadow: var(--shadow);
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 16px 0;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 12px;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      color: var(--text);
      font-weight: 600;
      font-size: 13px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 10px 8px;
      text-align: left;
    }}
    th {{
      color: var(--muted);
      font-weight: 700;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.02em;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
    }}
    .badge.red {{ color: var(--red); border-color: rgba(244,63,94,0.4); }}
    .badge.amber {{ color: var(--amber); border-color: rgba(245,158,11,0.4); }}
    .badge.green {{ color: var(--green); border-color: rgba(16,185,129,0.4); }}
    .muted {{ color: var(--muted); }}
  </style>
</head>
<body>
  <div class="page">
    <div class="card" style="display:flex; align-items:center; justify-content:space-between; gap:14px;">
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="height:44px;width:44px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:rgba(34,211,238,0.1);border:1px solid rgba(34,211,238,0.4);color:var(--accent);font-weight:700;font-size:18px;">H</div>
        <div>
          <div style="font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;">HCAI OPS</div>
          <div style="font-size:20px;font-weight:700;">Console Overview</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end;">
        <div class="pill">Total events: {total_events}</div>
        <div style="display:flex;gap:6px;">
          <span class="badge green">Sources {sources}</span>
          <span class="badge amber">Logs {log_count}</span>
          <span class="badge">Metrics {metric_count}</span>
          <span class="badge">Heartbeats {hb_count}</span>
        </div>
      </div>
    </div>

    <div class="summary-grid">
      <div class="card">
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;">Events</div>
        <div style="font-size:28px;font-weight:700;margin-top:4px;">{total_events}</div>
        <div class="muted" style="font-size:12px;">Last 50 shown below</div>
      </div>
      <div class="card">
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;">Sources</div>
        <div style="font-size:28px;font-weight:700;margin-top:4px;">{sources}</div>
        <div class="muted" style="font-size:12px;">Unique source_id count</div>
      </div>
      <div class="card">
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;">Logs</div>
        <div style="font-size:28px;font-weight:700;margin-top:4px;color:var(--amber);">{log_count}</div>
        <div class="muted" style="font-size:12px;">Log events</div>
      </div>
      <div class="card">
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;">Metrics</div>
        <div style="font-size:28px;font-weight:700;margin-top:4px;color:var(--accent);">{metric_count}</div>
        <div class="muted" style="font-size:12px;">Metric samples</div>
      </div>
      <div class="card">
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;">Errors</div>
        <div style="font-size:28px;font-weight:700;margin-top:4px;color:var(--red);">{level_counts.get('ERROR',0) + level_counts.get('CRITICAL',0)}</div>
        <div class="muted" style="font-size:12px;">Critical {level_counts.get('CRITICAL',0)} | Error {level_counts.get('ERROR',0)} | Warn {level_counts.get('WARNING',0)}</div>
      </div>
    </div>

    <div class="card">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <div>
          <div style="font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em;">Metrics</div>
          <div style="font-size:18px; font-weight:700;">Aggregated stats</div>
        </div>
      </div>
      <div style="overflow:auto;">
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>Source</th>
              <th>Avg</th>
              <th>Min</th>
              <th>Max</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {metric_table}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-top:14px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <div>
          <div style="font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em;">Recent events</div>
          <div style="font-size:18px; font-weight:700;">Latest 50</div>
        </div>
      </div>
      <div style="overflow:auto; max-height:400px;">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Source</th>
              <th>Type</th>
              <th>Level</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {events_table}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-top:14px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <div>
          <div style="font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em;">Critical & Errors</div>
          <div style="font-size:18px; font-weight:700;">Latest</div>
        </div>
      </div>
      <div style="overflow:auto; max-height:300px;">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Source</th>
              <th>Level</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {"".join(["<tr><td>{timestamp}</td><td>{source}</td><td>{level}</td><td>{message}</td></tr>".format(**r) for r in error_rows]) or "<tr><td colspan='4' style='text-align:center;color:var(--muted);padding:12px;'>No errors yet.</td></tr>"}
          </tbody>
        </table>
      </div>
    </div>

  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)
