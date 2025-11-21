# Installation

## Prerequisites

- Python 3.13
- Git
- Optional: Docker and Docker Compose

## Steps

```bash
git clone https://github.com/your-org/hcai_ops.git
cd hcai_ops
python -m venv venv
venv\Scripts\activate  # or source venv/bin/activate
pip install -e .
```

Launch the API:

```bash
uvicorn hcai_ops.api.server:app --host 0.0.0.0 --port 8000
```
