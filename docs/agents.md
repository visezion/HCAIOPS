# Agents

HCAI OPS agents run on edge nodes to collect telemetry and execute safe actions.

## Capabilities
- Heartbeats
- Metrics collection
- Log forwarding
- Safe command execution

## Lifecycle
- Install agent package
- Register with `/agent/ping`
- Send periodic reports via `/agent/report`

## Install the agent on another server/PC
Prereqs: Python 3.11+, network access to the API host.

### Linux or macOS
```bash
git clone https://github.com/visezion/HCAIOPS.git
cd HCAIOPS
python -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install -e hcai_ops_agent
cd hcai_ops_agent
python -m hcai_ops_agent.main --api-url http://<api-host>:8000 --api-key <api-key-if-required>
```

### Windows
```powershell
git clone https://github.com/visezion/HCAIOPS.git
cd HCAIOPS
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e hcai_ops_agent
cd hcai_ops_agent
python -m hcai_ops_agent.main --api-url http://<api-host>:8000 --api-key <api-key-if-required>
```

### Run as a service
- Linux: use `scripts/install_agent.sh` as a template to create a venv, place the agent, and add a systemd unit whose `ExecStart` calls the agent with `--api-url`.
- Windows: use `scripts/install_agent.ps1` and the service helpers under `hcai_ops_agent/installer`.

### Sanity check
From the agent host, confirm the API is reachable:  
`curl http://<api-host>:8000/health` should return `{"status": "ok"}`.
