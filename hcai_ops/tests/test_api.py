from fastapi.testclient import TestClient

from hcai_ops.api.server import app


client = TestClient(app)


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "HCAI OPS API running"


def test_risk_predict_without_model():
    resp = client.post("/risk/predict", json={"cpu_avg_5m": 0.5, "cpu_std_5m": 0.1, "error_rate_5m": 0.1, "log_error_count_5m": 1})
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_alert_predict_without_model():
    resp = client.post("/alerts/predict", json={"severity": 0.5, "cpu_at_alert": 0.6, "error_rate_at_alert": 0.1, "log_count_last_5m": 0})
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_action_recommend_without_model():
    resp = client.post("/actions/recommend", json={"cpu_before": 0.7, "error_rate_before": 0.2})
    assert resp.status_code == 200
    assert "error" in resp.json()
