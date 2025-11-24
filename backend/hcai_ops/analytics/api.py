from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends

from hcai_ops.analytics.store import EventStore
from hcai_ops.analytics.processors import (
    MetricAggregator,
    LogAnomalyDetector,
    CorrelationEngine,
    MetricThresholdDetector,
)
from hcai_ops.analytics import event_store

router = APIRouter(prefix="/analytics")


def get_store() -> EventStore:
    return event_store


@router.get("/summary")
def get_summary(store: EventStore = Depends(get_store)) -> dict:
    aggregator = MetricAggregator()
    return aggregator.aggregate(store.all())


@router.get("/timeseries")
def get_timeseries(minutes: int = 60, store: EventStore = Depends(get_store)) -> List[dict]:
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    events = store.since(cutoff)
    return [asdict(e) for e in events]


@router.get("/anomalies")
def get_anomalies(store: EventStore = Depends(get_store)) -> List[dict]:
    events = store.all()
    log_detector = LogAnomalyDetector()
    metric_detector = MetricThresholdDetector()
    log_anomalies = log_detector.detect(events)
    metric_anomalies = metric_detector.detect(events)
    return log_anomalies + metric_anomalies


@router.get("/correlations")
def get_correlations(store: EventStore = Depends(get_store)) -> List[dict]:
    engine = CorrelationEngine()
    return engine.correlate(store.all())
