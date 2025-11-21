// Shared navigation bar for HCAI OPS web pages.
// Call injectNav('<element-id>', '<active-id>') after the DOM element exists.
const HCAI_NAV_LINKS = [
  { id: "dashboard", label: "Dashboard", href: "/web/dashboard.html" },
  { id: "alerts", label: "Alerts", href: "/web/alerts.html" },
  { id: "logs", label: "Logs", href: "/web/logs.html" },
  { id: "agents", label: "Agents", href: "/web/agents.html" },
  { id: "metrics", label: "Metrics", href: "/web/metrics.html" },
  { id: "timeline", label: "Timeline", href: "/web/timeline.html" },
  { id: "assets", label: "Assets", href: "/web/assets.html" },
  { id: "console", label: "Console", href: "/console" },
  { id: "new-ui", label: "New UI", href: "/" },
  { id: "api", label: "API Docs", href: "/docs", target: "_blank", rel: "noreferrer" },
  { id: "redoc", label: "ReDoc", href: "/redoc", target: "_blank", rel: "noreferrer" }
];

function renderNav(activeId) {
  const items = HCAI_NAV_LINKS.map(link => {
    const isActive = link.id === activeId;
    const activeClasses = isActive ? "bg-sky-100 text-sky-800 border-sky-200" : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100";
    const target = link.target ? ` target="${link.target}"` : "";
    const rel = link.rel ? ` rel="${link.rel}"` : "";
    return `<a class="px-3 py-2 rounded-lg border text-sm font-medium transition ${activeClasses}" href="${link.href}" aria-label="${link.label}"${target}${rel}>${link.label}</a>`;
  }).join("<span class=\"text-slate-400\">•</span>");

  return `
    <div class="bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex flex-wrap gap-2 items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="h-10 w-10 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center text-lg font-bold border border-sky-200">H</div>
        <div>
          <div class="text-lg font-semibold text-slate-900">HCAI OPS</div>
          <div class="text-xs text-slate-500">Unified navigation</div>
        </div>
      </div>
      <div class="flex flex-wrap gap-2 text-xs text-slate-600 items-center">
        ${items}
      </div>
    </div>
  `;
}

function injectNav(elementId, activeId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = renderNav(activeId);
}
