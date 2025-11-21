function timelinePage() {
    return {

        events: [],
        expanded: {},

        filters: {
            type: "",
            search: ""
        },

        async fetchEvents() {
            let res = await fetch("/events/recent");
            this.events = await res.json();
        },

        get filteredEvents() {

            return this.events.filter(ev => {

                let ok = true;

                if (this.filters.type) {
                    if (ev.event_type !== this.filters.type)
                        ok = false;
                }

                if (this.filters.search) {
                    const s = this.filters.search.toLowerCase();

                    const combined =
                        JSON.stringify(ev).toLowerCase();

                    if (!combined.includes(s))
                        ok = false;
                }

                return ok;
            });
        },

        summary(ev) {
            if (ev.event_type === "metric") {
                return `${ev.metric_name}: ${ev.metric_value}`;
            }
            if (ev.event_type === "alert") {
                return `Alert severity ${ev.alert_severity}`;
            }
            if (ev.event_type === "log") {
                return ev.log_message || "Log entry";
            }
            if (ev.event_type === "heartbeat") {
                return "Heartbeat received";
            }
            if (ev.event_type === "automation") {
                return "Automation action executed";
            }
            return "Event";
        },

        iconClass(type) {
            return {
                metric:    "bg-blue-500",
                alert:     "bg-red-600",
                log:       "bg-yellow-400",
                heartbeat: "bg-green-500",
                automation:"bg-purple-600"
            }[type] || "bg-gray-400";
        },

        typeBadge(type) {
            return {
                metric:    "bg-blue-100 text-blue-700",
                alert:     "bg-red-100 text-red-700",
                log:       "bg-yellow-100 text-yellow-700",
                heartbeat: "bg-green-100 text-green-700",
                automation:"bg-purple-100 text-purple-700"
            }[type] || "bg-gray-100 text-gray-700";
        },

        toggleExpand(id) {
            this.expanded[id] = !this.expanded[id];
        },

        formatJSON(obj) {
            return JSON.stringify(obj, null, 2);
        },

        init() {
            this.fetchEvents();
            setInterval(() => this.fetchEvents(), 10000);
        }
    }
}
