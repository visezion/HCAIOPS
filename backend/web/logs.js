function logsPage() {
    return {

        logs: [],
        expanded: {},

        filters: {
            level: "",
            search: ""
        },

        count: {
            CRITICAL: 0,
            ERROR: 0,
            WARNING: 0,
            INFO: 0,
            DEBUG: 0
        },

        get filteredLogs() {
            return this.logs.filter(l => {
                let ok = true;

                if (this.filters.level) {
                    if (l.log_level !== this.filters.level)
                        ok = false;
                }

                if (this.filters.search) {
                    const s = this.filters.search.toLowerCase();
                    if (
                        !l.log_message.toLowerCase().includes(s) &&
                        !l.source_id.toLowerCase().includes(s) &&
                        !l.extras.raw_header.toLowerCase().includes(s)
                    ) {
                        ok = false;
                    }
                }

                return ok;
            });
        },

        levelColor(level) {
            return {
                CRITICAL: "bg-red-600 text-white",
                ERROR: "bg-orange-500 text-white",
                WARNING: "bg-yellow-400 text-gray-900",
                INFO: "bg-blue-500 text-white",
                DEBUG: "bg-gray-700 text-white"
            }[level] || "bg-gray-300 text-black";
        },

        toggleExpand(id) {
            this.expanded[id] = !this.expanded[id];
        },

        updateCounters() {
            this.count = {
                CRITICAL: this.logs.filter(l => l.log_level === "CRITICAL").length,
                ERROR: this.logs.filter(l => l.log_level === "ERROR").length,
                WARNING: this.logs.filter(l => l.log_level === "WARNING").length,
                INFO: this.logs.filter(l => l.log_level === "INFO").length,
                DEBUG: this.logs.filter(l => l.log_level === "DEBUG").length
            };
        },

        async fetchLogs() {
            let res = await fetch("/logs/recent");
            let data = await res.json();

            this.logs = data;
            this.updateCounters();
        },

        init() {
            this.fetchLogs();
            setInterval(() => this.fetchLogs(), 10000);
        }
    }
}
