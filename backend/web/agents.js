function agentsPage() {
    return {
        agents: [],
        sources: [],
        modalOpen: false,
        selectedAgent: null,

        filters: {
            source_id: "",
            search: ""
        },

        get filteredAgents() {
            return this.agents.filter(a => {
                let ok = true;

                // Filter by source
                if (this.filters.source_id && a.source_id !== this.filters.source_id)
                    ok = false;

                // Search in name or description
                if (this.filters.search) {
                    let q = this.filters.search.toLowerCase();
                    if (!a.name.toLowerCase().includes(q) &&
                        !a.description.toLowerCase().includes(q))
                        ok = false;
                }

                return ok;
            });
        },

        async fetchAgents() {
            let res = await fetch("/agents");
            let data = await res.json();
            this.agents = data;

            // build unique sources
            this.sources = [...new Set(this.agents.map(a => a.source_id))];
        },

        viewDetails(agent) {
            this.selectedAgent = agent;
            this.modalOpen = true;
        },

        async restartAgent(id) {
            await fetch(`/agents/${id}/restart`, {
                method: "POST"
            });
            this.fetchAgents();
        },

        init() {
            this.fetchAgents();
            setInterval(() => this.fetchAgents(), 15000);
        }
    }
}
