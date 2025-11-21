from datetime import datetime, timedelta

from hcai_ops.data.schemas import HCaiEvent
from hcai_ops.models.action_model import ActionRecommender
from hcai_ops.models.alert_model import AlertImportanceModel
from hcai_ops.models.risk_model import RiskModel


def _base_time():
    return datetime(2025, 1, 1, 0, 0, 0)


def test_risk_model_training_and_prediction():
    base = _base_time()
    events = [
        HCaiEvent(timestamp=base, source_id="s1", event_type="metric", metric_name="cpu", metric_value=0.4),
        HCaiEvent(
            timestamp=base + timedelta(minutes=1),
            source_id="s1",
            event_type="metric",
            metric_name="error_rate",
            metric_value=0.2,
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=2),
            source_id="s1",
            event_type="log",
            log_message="error",
            log_level="ERROR",
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=8),
            source_id="s1",
            event_type="incident",
            incident_label="network",
        ),
    ]

    model = RiskModel()
    metrics = model.fit_from_events(events)
    assert "accuracy" in metrics and "f1" in metrics

    prob = model.predict_from_features(
        {"cpu_avg_5m": 0.5, "cpu_std_5m": 0.1, "error_rate_5m": 0.2, "log_error_count_5m": 1}
    )
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_alert_importance_model():
    base = _base_time()
    events = [
        HCaiEvent(
            timestamp=base,
            source_id="s1",
            event_type="alert",
            alert_id="a1",
            metric_value=0.9,
            extras={"severity": 0.9},
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=1),
            source_id="s1",
            event_type="metric",
            metric_name="cpu",
            metric_value=0.7,
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=1, seconds=30),
            source_id="s1",
            event_type="metric",
            metric_name="error_rate",
            metric_value=0.3,
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=2),
            source_id="s1",
            event_type="log",
            log_message="warn",
            log_level="INFO",
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=3),
            source_id="s1",
            event_type="operator_action",
            alert_id="a1",
            op_user_id="op-1",
            op_action_type="ack",
            applied_action="scale",
            outcome_label="resolved",
        ),
    ]

    model = AlertImportanceModel()
    metrics = model.fit_from_events(events)
    assert "precision" in metrics and "recall" in metrics

    prob = model.predict_importance(
        {"severity": 0.8, "cpu_at_alert": 0.7, "error_rate_at_alert": 0.3, "log_count_last_5m": 0}
    )
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_action_recommender():
    base = _base_time()
    events = [
        HCaiEvent(
            timestamp=base,
            source_id="s1",
            event_type="incident",
            incident_label="network",
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=1),
            source_id="s1",
            event_type="metric",
            metric_name="cpu",
            metric_value=0.8,
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=1),
            source_id="s1",
            event_type="metric",
            metric_name="error_rate",
            metric_value=0.4,
        ),
        HCaiEvent(
            timestamp=base + timedelta(minutes=2),
            source_id="s1",
            event_type="operator_action",
            applied_action="restart_service",
            outcome_label="resolved",
        ),
    ]

    recommender = ActionRecommender()
    recommender.fit_from_events(events, n_neighbors=1)

    action = recommender.recommend_action({"cpu_before": 0.75, "error_rate_before": 0.35})
    assert isinstance(action, str)
