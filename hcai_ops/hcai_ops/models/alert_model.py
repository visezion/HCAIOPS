from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from ..data.preprocess import build_alert_training_table
from ..data.schemas import HCaiEvent
from .utils import ensure_feature_order, evaluate_classification, split_dataset


@dataclass
class AlertImportanceModel:
    """
    Classifies alerts as important or noise based on context features.
    """

    feature_cols: Sequence[str] = field(
        default_factory=lambda: [
            "severity",
            "cpu_at_alert",
            "error_rate_at_alert",
            "log_count_last_5m",
        ]
    )
    label_col: str = "label"
    model: Optional[GradientBoostingClassifier] = None

    def fit_from_events(self, events: List[HCaiEvent]) -> Dict[str, float]:
        """
        Build alert training table from events, train the model,
        and return evaluation metrics.
        Handles very small or single-class datasets safely.
        """
        df = build_alert_training_table(events)
        if df.empty or df[self.label_col].isna().all():
            return {"precision": 0.0, "recall": 0.0, "note": "no training samples"}

        df = df.dropna(subset=[self.label_col])

        # NEW: Prevent training on single-row or single-class datasets
        if df[self.label_col].nunique() < 2 or len(df) < 2:
            self.model = None
            return {"precision": 0.0, "recall": 0.0, "note": "insufficient data"}

        X_train, X_test, y_train, y_test = split_dataset(
            df, self.feature_cols, self.label_col
        )

        self.model = GradientBoostingClassifier()
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)

        return evaluate_classification(y_test, y_pred)

    def predict_importance(self, features: Dict[str, Any]) -> float:
        """
        Predict the probability that an alert is important.
        If the model is untrained (small dataset), returns a safe fallback.
        """
        if self.model is None:
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
