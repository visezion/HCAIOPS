from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.dummy import DummyClassifier

from ..data.preprocess import build_risk_training_table
from ..data.schemas import HCaiEvent
from .utils import ensure_feature_order, evaluate_classification, split_dataset


@dataclass
class RiskModel:
    """
    Predicts the probability of an incident in the next time window
    based on aggregated metrics and log features.
    """

    feature_cols: Sequence[str] = field(
        default_factory=lambda: [
            "cpu_avg_5m",
            "cpu_std_5m",
            "error_rate_5m",
            "log_error_count_5m",
        ]
    )
    label_col: str = "incident_in_next_10m"
    model: Optional[GradientBoostingClassifier] = None

    def fit_from_events(self, events: List[HCaiEvent]) -> Dict[str, float]:
        """
        Build the risk training table from events, train the model,
        and return evaluation metrics on a held-out test set.
        Handles very small datasets gracefully.
        """
        df = build_risk_training_table(events)
        if df.empty or df[self.label_col].isna().all():
            return {"accuracy": 0.0, "f1": 0.0, "note": "no training samples"}

        df = df.dropna(subset=[self.label_col])

        # NEW: Prevent crash when there is only 1 class or dataset is too small
        features = ensure_feature_order(df, self.feature_cols)
        labels = df[self.label_col].to_numpy()

        if df[self.label_col].nunique() < 2 or len(df) < 5:
            # Train a baseline model so downstream predictions still work.
            self.model = DummyClassifier(strategy="most_frequent")
            self.model.fit(features, labels)
            y_pred = self.model.predict(labels)
            metrics = evaluate_classification(labels, y_pred)
            metrics["note"] = "trained baseline on single-class or small dataset"
            return metrics

        X_train, X_test, y_train, y_test = split_dataset(df, self.feature_cols, self.label_col)

        self.model = GradientBoostingClassifier()
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)

        return evaluate_classification(y_test, y_pred)

    def predict_from_features(self, features: Dict[str, Any]) -> float:
        """
        Predict risk probability from a single feature dict.
        Returns a float between 0 and 1.
        """
        if self.model is None:
            # fallback safe value
            return 0.0

        feat_df = pd.DataFrame([features])
        ordered = ensure_feature_order(feat_df, self.feature_cols)
        proba = self.model.predict_proba(ordered)
        return float(proba[0, 1])

    def save(self, path: str) -> None:
        """
        Save model and configuration to a file using joblib.
        """
        joblib.dump(
            {"model": self.model, "feature_cols": list(self.feature_cols), "label_col": self.label_col},
            path,
        )

    def load(self, path: str) -> None:
        """
        Load model and configuration from a joblib file.
        """
        payload = joblib.load(path)
        self.model = payload.get("model")
        self.feature_cols = payload.get("feature_cols", self.feature_cols)
        self.label_col = payload.get("label_col", self.label_col)
