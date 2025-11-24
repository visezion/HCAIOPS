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
# Metrics require psutil; install it if not present
pip install psutil
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
# Metrics require psutil; install it if not present
python -m pip install psutil
# Windows event logs require pywin32
python -m pip install pywin32
cd hcai_ops_agent
python -m hcai_ops_agent.main --api-url http://<api-host>:8000 --api-key <api-key-if-required>
```

### Run as a service
- Linux: use `scripts/install_agent.sh` as a template to create a venv, place the agent, and add a systemd unit whose `ExecStart` calls the agent with `--api-url`.
- Windows: use `scripts/install_agent.ps1` and the service helpers under `hcai_ops_agent/installer`.

### Connect through the Cloudflare tunnel (hcaiops.vicezion.com)
- Confirm the tunnel maps `https://hcaiops.vicezion.com` to your local API on `127.0.0.1:8000`.
- Point the agent at that hostname either via env vars or CLI:
  - `HCAI_AGENT_API_URL=https://hcaiops.vicezion.com HCAI_AGENT_TOKEN=<token> python -m hcai_ops_agent.main`
  - `python -m hcai_ops_agent.main --api-url https://hcaiops.vicezion.com --token <token>`
- The config file lives at `%ProgramData%/HCAI_AGENT/config.json` on Windows or `~/.hcai_agent/config.json` elsewhere; the agent persists the URL/token there unless `--no-save` is provided.
- Open `https://hcaiops.vicezion.com` in the browser; dashboard values should populate once the agent begins posting telemetry.

### Sanity check
From the agent host, confirm the API is reachable:  
`curl http://<api-host>:8000/health` should return `{"status": "ok"}`.
