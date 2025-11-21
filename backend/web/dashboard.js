function dashboard() {
  return {
    endpoints: {
      metrics: "/api/analytics/metrics/summary",
      logs: "/api/events/recent",
      insights: "/api/intelligence/insights",
      cooling: "/api/control/cooling",
      agent: "/api/agent/run",
    },
    refreshSeconds: 10,
    latencyMs: 0,
    metrics: {
      cpu_usage: 0,
      memory_usage: 0,
      error_rate: 0,
      log_rate: 0,
    },
    history: {
      cpu_usage: [],
      memory_usage: [],
      error_rate: [],
      log_rate: [],
    },
    logs: [],
    logFilter: { level: "", source: "" },
    insights: [],
    cooling: { mode: "auto", fan_speed: 50, target_temp: 22 },
    controlMessage: "",
    agentCommand: "",
    agentResult: "",
    agentBusy: false,

    init() {
      this.refreshAll();
      setInterval(() => this.refreshAll(), this.refreshSeconds * 1000);
    },

    metricCards() {
      return [
        { key: "cpu_usage", label: "CPU Usage", value: this.metrics.cpu_usage, history: this.history.cpu_usage },
        { key: "memory_usage", label: "Memory Usage", value: this.metrics.memory_usage, history: this.history.memory_usage },
        { key: "error_rate", label: "Error Rate", value: this.metrics.error_rate, history: this.history.error_rate },
        { key: "log_rate", label: "Log Volume", value: this.metrics.log_rate, history: this.history.log_rate },
      ];
    },

    refreshAll() {
      this.refreshMetrics();
      this.refreshLogs();
      this.refreshInsights();
    },

    async refreshMetrics() {
      const start = performance.now();
      try {
        const res = await fetch(this.endpoints.metrics);
        const json = await res.json();
        this.latencyMs = performance.now() - start;

        const mapVal = (key) => Number(json[key] || 0);
        this.metrics.cpu_usage = mapVal("cpu_usage");
        this.metrics.memory_usage = mapVal("memory_usage");
        this.metrics.error_rate = mapVal("error_rate");
        this.metrics.log_rate = mapVal("log_rate");

        ["cpu_usage", "memory_usage", "error_rate", "log_rate"].forEach((k) => {
          this.history[k].push({ id: Date.now() + k, val: Math.min(1, Math.max(0, this.metrics[k])) });
          if (this.history[k].length > 30) this.history[k].shift();
        });
      } catch (e) {
        this.latencyMs = performance.now() - start;
      }
    },

    async refreshLogs() {
      try {
        const res = await fetch(`${this.endpoints.logs}?limit=100`);
        const json = await res.json();
        this.logs = Array.isArray(json) ? json : json.events || [];
      } catch (e) {
        this.logs = [];
      }
    },

    async refreshInsights() {
      try {
        const res = await fetch(this.endpoints.insights);
        const json = await res.json();
        if (Array.isArray(json)) {
          this.insights = json;
        } else if (Array.isArray(json.insights)) {
          this.insights = json.insights;
        } else {
          this.insights = [];
        }
      } catch (e) {
        this.insights = [];
      }
    },

    async applyCooling() {
      try {
        const res = await fetch(this.endpoints.cooling, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.cooling),
        });
        const json = await res.json();
        this.controlMessage = json.message || "Applied cooling settings.";
      } catch (e) {
        this.controlMessage = "Failed to apply cooling.";
      }
    },

    async runAgentCommand() {
      if (!this.agentCommand) return;
      this.agentBusy = true;
      this.agentResult = "";
      try {
        const res = await fetch(this.endpoints.agent, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: this.agentCommand }),
        });
        const json = await res.json();
        this.agentResult = json.summary || JSON.stringify(json);
      } catch (e) {
        this.agentResult = "Agent unavailable.";
      } finally {
        this.agentBusy = false;
      }
    },

    filteredLogs() {
      return this.logs.filter((l) => {
        const levelOk = !this.logFilter.level || (l.log_level || "").toUpperCase() === this.logFilter.level;
        const sourceOk = !this.logFilter.source || (l.source_id || "").includes(this.logFilter.source);
        return levelOk && sourceOk;
      });
    },

    systemStatusLabel() {
      if (this.metrics.error_rate > 0.3) return "Incident";
      if (this.metrics.error_rate > 0.1) return "Degraded";
      return "OK";
    },

    latencyClass() {
      if (this.latencyMs < 150) return "bg-emerald-400";
      if (this.latencyMs < 400) return "bg-amber-400";
      return "bg-rose-400";
    },

    latencyLabel() {
      if (!this.latencyMs) return "n/a";
      return `${this.latencyMs.toFixed(0)} ms`;
    },

    formatPercent(v) {
      return `${Math.round((v || 0) * 100)}%`;
    },

    formatTime(ts) {
      try {
        return new Date(ts).toLocaleTimeString();
      } catch (e) {
        return ts;
      }
    },

    badgeClass(v) {
      if (v > 0.9) return "bg-rose-500/20 text-rose-200";
      if (v > 0.6) return "bg-amber-500/20 text-amber-200";
      return "bg-emerald-500/20 text-emerald-200";
    },

    severityLabel(v) {
      if (v > 0.9) return "Critical";
      if (v > 0.6) return "High";
      if (v > 0.3) return "Moderate";
      return "Normal";
    },

    logLevelClass(level) {
      const lv = (level || "").toUpperCase();
      if (lv === "ERROR" || lv === "CRITICAL") return "bg-rose-500/20 text-rose-200";
      if (lv === "WARNING") return "bg-amber-500/20 text-amber-200";
      return "bg-slate-700 text-slate-200";
    },
  };
}
