function alertsPage() {
    return {

        alerts: [],
        expanded: {},

        filters: {
            severity: "",
            search: ""
        },

        count: {
            CRITICAL: 0,
            ERROR: 0,
            WARNING: 0,
            INFO: 0
        },

        get filteredAlerts() {
            return this.alerts.filter(a => {
                let ok = true;

                if (this.filters.severity) {
                    if (a.severity !== this.filters.severity)
                        ok = false;
                }

                if (this.filters.search) {
                    const q = this.filters.search.toLowerCase();
                    if (
                        !a.message.toLowerCase().includes(q) &&
                        !a.source_id.toLowerCase().includes(q)
                    ) {
                        ok = false;
                    }
                }

                return ok;
            });
        },

        severityColor(level) {
            return {
                CRITICAL: "bg-red-600 text-white",
                ERROR: "bg-orange-500 text-white",
                WARNING: "bg-yellow-400 text-gray-900",
                INFO: "bg-blue-500 text-white"
            }[level] || "bg-gray-300 text-black";
        },

        toggleExpand(id) {
            this.expanded[id] = !this.expanded[id];
        },

        acknowledge(id) {
            // no backend call for now
            console.log("Acknowledged alert:", id);
        },

        updateCounters() {
            this.count = {
                CRITICAL: this.alerts.filter(a => a.severity === "CRITICAL").length,
                ERROR: this.alerts.filter(a => a.severity === "ERROR").length,
                WARNING: this.alerts.filter(a => a.severity === "WARNING").length,
                INFO: this.alerts.filter(a => a.severity === "INFO").length
            };
        },

        async fetchAlerts() {
            let res = await fetch("/alerts/recent");
            let data = await res.json();

            this.alerts = data;
            this.updateCounters();
        },

        init() {
            this.fetchAlerts();
            setInterval(() => this.fetchAlerts(), 10000);
        }
    }
}
