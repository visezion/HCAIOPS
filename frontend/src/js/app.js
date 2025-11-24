import '../css/tailwind.css';
import Alpine from 'alpinejs';
import 'flowbite';
import {
  getMetricsSummary,
  getRecentEvents,
  getRecentLogs,
  getAutomationJobs,
  triggerAutomationJob,
  getAgentsStatus,
  getIntelligenceOverview,
  getLogAnomalies,
  sendControlAction,
  submitFeedback,
} from './api';

const componentCache = {};

async function getPartial(path) {
  if (componentCache[path]) return componentCache[path];
  const res = await fetch(path);
  const html = await res.text();
  componentCache[path] = html;
  return html;
}

async function hydrateIncludes(root) {
  const includes = Array.from(root.querySelectorAll('[data-include]')).filter(
    (node) => node.dataset.hydrated !== 'true'
  );

  for (const node of includes) {
    const path = node.dataset.include;
    try {
      const html = await getPartial(path);
      node.innerHTML = html;
      node.dataset.hydrated = 'true';
      Alpine.initTree(node);
    } catch (error) {
      console.error('Failed to include', path, error);
    }
  }
}

async function hydrateComponents(root) {
  const components = Array.from(root.querySelectorAll('[data-component]')).filter(
    (node) => node.dataset.hydrated !== 'true'
  );

  for (const node of components) {
    const name = node.dataset.component;
    try {
      const html = await getPartial(`/src/components/${name}.html`);
      node.innerHTML = html;
      node.dataset.hydrated = 'true';
      Alpine.initTree(node);
    } catch (error) {
      console.error('Failed to load component', name, error);
    }
  }
}

const rehydrateLater = () => setTimeout(() => hydrateComponents(document), 0);

document.addEventListener('alpine:init', () => {
  Alpine.store('theme', {
    mode: 'light',
    get isDark() {
      return false;
    },
    apply() {
      document.documentElement.classList.remove('dark');
    },
    toggle() {
      this.apply();
    },
  });

  // Central Alpine store powering the dashboard tabs and API calls
  Alpine.store('hcai', {
    activeTab: 'overview',
    loadingMetrics: false,
    loadingLogs: false,
    loadingAgents: false,
    loadingAutomation: false,
    loadingIntelligence: false,
    loadingControlAction: false,

    metricsSummary: {},
    recentEvents: [],
    controlPlan: { incidents: [], recommendations: {}, actions: {}, risk: {} },
    agents: [],
    automationJobs: [],
    anomalies: [],
    feedbackForm: {
      incidentId: '',
      decision: 'agree',
      action: '',
      notes: '',
    },
    feedbackStatus: '',
    feedbackError: '',

    logFilter: '',
    controlTarget: 'cluster',
    controlAction: 'scale_up',
    controlNote: '',
    controlPayload: '{\n  "dry_run": true\n}',

    successMessage: '',
    errorMessage: '',
    hasLoaded: {
      overview: false,
      logs: false,
      agents: false,
      automation: false,
      intelligence: false,
    },

    async init() {
      Alpine.store('theme').apply();
      await hydrateIncludes(document);
      await hydrateComponents(document);
      await this.loadOverview();
    },

    setTab(tabName) {
      this.activeTab = tabName;
      if (tabName === 'logs' && !this.hasLoaded.logs) this.loadLogs();
      if (tabName === 'agents' && !this.hasLoaded.agents) this.loadAgents();
      if (tabName === 'automation' && !this.hasLoaded.automation) this.loadAutomation();
      if (tabName === 'intelligence' && !this.hasLoaded.intelligence) this.loadIntelligence();
      if (tabName === 'overview' && !this.hasLoaded.overview) this.loadOverview();
    },

    async loadOverview() {
      await Promise.all([this.loadMetrics(), this.loadAgents(), this.loadIntelligence(), this.loadLogs(), this.loadAutomation()]);
      this.hasLoaded.overview = true;
    },

    async loadMetrics() {
      this.loadingMetrics = true;
      try {
        const summary = await getMetricsSummary();
        this.metricsSummary = summary || {};
        rehydrateLater();
      } catch (error) {
        this.notifyError(error.message || 'Failed to load metrics');
      } finally {
        this.loadingMetrics = false;
      }
    },

    async loadLogs() {
      this.loadingLogs = true;
      try {
        const logs = await getRecentLogs(200).catch(() => getRecentEvents(360));
        this.recentEvents = Array.isArray(logs)
          ? logs.map((event, idx) => ({
              id: event.id || event.incident_id || `evt-${idx}`,
              timestamp: event.timestamp,
              source_id: event.source_id || 'unknown',
              log_level: (event.log_level || (event.event_type || '').toUpperCase() || 'INFO').toUpperCase(),
              log_message: (event.log_message || event.metric_name || event.event_type || '').toString(),
              event_type: event.event_type || 'log',
            }))
          : [];
        rehydrateLater();
        this.hasLoaded.logs = true;
      } catch (error) {
        this.notifyError(error.message || 'Failed to load events');
      } finally {
        this.loadingLogs = false;
      }
    },

    async loadAgents() {
      this.loadingAgents = true;
      try {
        const agents = await getAgentsStatus();
        this.agents = (agents || []).map((agent) => {
          const lastSeen = agent.last_seen ? new Date(agent.last_seen) : null;
          const now = new Date();
          const agoMs = lastSeen ? now - lastSeen : null;
          const agoMinutes = agoMs !== null ? Math.max(0, Math.floor(agoMs / 60000)) : null;
          const agoDisplay =
            agoMinutes === null
              ? 'unknown'
              : agoMinutes < 1
              ? 'just now'
              : agoMinutes < 60
              ? `${agoMinutes}m ago`
              : `${Math.floor(agoMinutes / 60)}h ago`;
          return {
            id: agent.id || agent.name,
            name: agent.name || agent.id || 'agent',
            status: agent.status || 'unknown',
            latency: agent.latency || null,
            heartbeat: agent.last_seen || null,
            lastSeenDisplay: agoDisplay,
            risk: agent.risk || 0,
            errors: agent.errors || 0,
          };
        });
        rehydrateLater();
        this.hasLoaded.agents = true;
      } catch (error) {
        this.notifyError(error.message || 'Failed to load agents');
      } finally {
        this.loadingAgents = false;
      }
    },

    async loadAutomation() {
      this.loadingAutomation = true;
      try {
        let plan = await getAutomationJobs();
        if (!plan || !plan.incidents) {
          try {
            const res = await fetch('/console/plan');
            if (res.ok) plan = await res.json();
          } catch (e) {
            // ignore fallback errors; handled below
          }
        }
        const incidents = plan?.incidents || [];
        const actions = plan?.actions || {};
        this.controlPlan = plan || { incidents: [], recommendations: {}, actions: {}, risk: {} };
        if (!this.feedbackForm.incidentId && incidents.length) {
          this.feedbackForm.incidentId = incidents[0].incident_id;
        }
        this.automationJobs = incidents.flatMap((inc) => {
          const incActions = actions[inc.incident_id] || [];
          return incActions.map((act, idx) => ({
            id: `${inc.incident_id || 'inc'}-${idx}`,
            incident_id: inc.incident_id,
            source_id: inc.source_id,
            name: act.action || 'automation',
            description: act.reason || inc.summary || 'Policy derived action',
            state: inc.status || 'planned',
            severity: inc.severity,
            updated_at: new Date().toISOString(),
          }));
        });
        rehydrateLater();
        this.hasLoaded.automation = true;
      } catch (error) {
        this.notifyError(error.message || 'Failed to load automation');
      } finally {
        this.loadingAutomation = false;
      }
    },

    async submitFeedbackForm() {
      this.feedbackStatus = '';
      this.feedbackError = '';
      try {
        const incident = (this.controlPlan.incidents || []).find(
          (i) => i.incident_id === this.feedbackForm.incidentId
        );
        const payload = {
          incident_id: this.feedbackForm.incidentId,
          source_id: incident?.source_id,
          accepted: this.feedbackForm.decision === 'agree',
          correct: this.feedbackForm.decision === 'agree',
          action: this.feedbackForm.action || (this.controlPlan.actions?.[incident?.incident_id]?.[0]?.action || ''),
          notes: this.feedbackForm.notes,
          severity: incident?.severity,
          recommended_action: this.controlPlan.recommendations?.[incident?.incident_id]?.recommended_action,
          risk: incident?.risk,
        };
        await submitFeedback(payload);
        this.feedbackStatus = 'Thanks, your feedback was recorded.';
        this.feedbackForm.notes = '';
        this.feedbackForm.action = '';
      } catch (error) {
        this.feedbackError = error.message || 'Failed to submit feedback';
      }
    },

    async runAutomation(jobId) {
      this.loadingAutomation = true;
      try {
        await triggerAutomationJob({ dry_run: false, job_id: jobId });
        this.notifySuccess(`Triggered automation ${jobId || ''}`.trim());
        await this.loadAutomation();
      } catch (error) {
        this.notifyError(error.message || 'Automation run failed');
      } finally {
        this.loadingAutomation = false;
      }
    },

    async loadIntelligence() {
      this.loadingIntelligence = true;
      try {
        const [overview, logAnoms] = await Promise.all([getIntelligenceOverview(), getLogAnomalies()]);
        const incidents = overview?.incidents || [];
        const riskMap = overview?.risk || {};
        const anomalyItems = (logAnoms || []).map((anom, idx) => ({
          id: anom.source_id ? `log-${anom.source_id}-${idx}` : `log-${idx}`,
          source_id: anom.source_id,
          severity: anom.anomaly ? 'high' : 'low',
          status: anom.anomaly ? 'open' : 'observing',
          summary: `Error spikes: ${anom.error_count} errors`,
          risk: anom.error_count || 0,
          score: anom.error_count || 0,
          timestamp: new Date().toISOString(),
        }));
        const incidentItems = incidents.map((inc, idx) => ({
          id: inc.incident_id || `inc-${idx}`,
          source_id: inc.source_id,
          severity: inc.severity,
          status: inc.status,
          summary: inc.summary,
          risk: inc.risk,
          score: (riskMap?.[inc.source_id]?.risk || inc.risk || 0).toFixed(1),
          timestamp: new Date().toISOString(),
        }));
        this.anomalies = [...incidentItems, ...anomalyItems];
        rehydrateLater();
        this.hasLoaded.intelligence = true;
      } catch (error) {
        this.notifyError(error.message || 'Failed to load intelligence');
      } finally {
        this.loadingIntelligence = false;
      }
    },

    async sendControlActionFromUI() {
      this.loadingControlAction = true;
      try {
        let parsedPayload = {};
        if (this.controlPayload?.trim()) {
          parsedPayload = JSON.parse(this.controlPayload);
        }
        const payload = {
          target: this.controlTarget,
          action: this.controlAction,
          note: this.controlNote,
          dry_run: false,
          ...parsedPayload,
        };
        await sendControlAction(payload);
        this.notifySuccess(`Sent control: ${this.controlAction}`);
      } catch (error) {
        this.notifyError(error.message || 'Failed to send control');
      } finally {
        this.loadingControlAction = false;
      }
    },

    clearMessage(type) {
      if (type === 'success') this.successMessage = '';
      if (type === 'error') this.errorMessage = '';
    },

    notifySuccess(message) {
      this.successMessage = message;
      setTimeout(() => this.clearMessage('success'), 4000);
    },

    notifyError(message) {
      this.errorMessage = message;
      setTimeout(() => this.clearMessage('error'), 5000);
    },

    metricsList() {
      const summary = this.metricsSummary || {};
      const fmt = (value, digits = 1) => {
        if (value === null || value === undefined) return value;
        const num = Number(value);
        if (Number.isNaN(num)) return value;
        return num.toFixed(digits);
      };
      if (Array.isArray(summary)) {
        return summary.map((item) => {
          const avg = item.metric_value ?? item.avg ?? 0;
          const delta = fmt((item.max ?? avg) - (item.min ?? avg));
          return {
            name: item.metric_name,
            source: item.source_id,
            value: fmt(avg),
            delta,
            window: 'live',
            score: Math.min(100, Math.round((avg || 0) * 100)),
            updated_at: item.history?.[item.history.length - 1]?.timestamp || new Date().toISOString(),
          };
        });
      }

      return Object.entries(summary).map(([key, stats]) => {
        const [metric_name, source_id] = key.split(':');
        const avg = stats?.avg ?? 0;
        const delta = fmt((stats?.max ?? avg) - (stats?.min ?? avg));
        return {
          name: metric_name,
          source: source_id,
          value: fmt(avg),
          delta,
          window: 'live',
          score: Math.min(100, Math.round((avg || 0) * 100)),
          updated_at: new Date().toISOString(),
        };
      });
    },

    filteredEvents() {
      const term = this.logFilter.toLowerCase();
      return this.recentEvents.filter((event) => {
        if (!term) return true;
        return (
          (event.log_level || '').toLowerCase().includes(term) ||
          (event.log_message || '').toLowerCase().includes(term) ||
          (event.source_id || '').toLowerCase().includes(term)
        );
      });
    },
  });
});

window.Alpine = Alpine;
Alpine.start();
