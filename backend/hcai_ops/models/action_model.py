from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from ..data.preprocess import build_action_training_table
from ..data.schemas import HCaiEvent
from .utils import ensure_feature_order


@dataclass
class ActionRecommender:
    """
    Recommends an action for an incident based on similar past contexts.
    Uses a simple nearest neighbor search in feature space.
    """

    feature_cols: Sequence[str] = field(
        default_factory=lambda: [
            "cpu_before",
            "error_rate_before",
        ]
    )
    model: Optional[NearestNeighbors] = None
    action_history: Optional[pd.DataFrame] = None

    def fit_from_events(self, events: List[HCaiEvent], n_neighbors: int = 5) -> None:
        """
        Build the action training table from events and fit the nearest neighbors model.
        Stores the full training DataFrame in action_history.
        """
        df = build_action_training_table(events)
        if "applied_action" not in df.columns or df.empty:
            self.model = None
            self.action_history = None
            return

        df = df.dropna(subset=["applied_action"])
        if df.empty:
            self.model = None
            self.action_history = None
            return

        self.action_history = df.reset_index(drop=True)
        features = ensure_feature_order(self.action_history, self.feature_cols)
        neighbors = min(n_neighbors, len(self.action_history))
        self.model = NearestNeighbors(n_neighbors=neighbors)
        self.model.fit(features)

    def recommend_action(self, context_features: Dict[str, Any]) -> Optional[str]:
        """
        Recommend an action based on nearest neighbors in the action history.
        Returns the most common applied_action among neighbors or None if no history.
        """
        if self.model is None or self.action_history is None or self.action_history.empty:
            return None

        feat_df = pd.DataFrame([context_features])
        features = ensure_feature_order(feat_df, self.feature_cols)
        distances, indices = self.model.kneighbors(features, return_distance=True)
        neighbor_rows = self.action_history.iloc[indices[0]]
        if neighbor_rows.empty:
            return None

        action_counts = neighbor_rows["applied_action"].value_counts()
        return action_counts.idxmax() if not action_counts.empty else None

    def save(self, path: str) -> None:
        """
        Save the recommender model, feature list, and action history.
        """
        joblib.dump(
            {
                "model": self.model,
                "feature_cols": list(self.feature_cols),
                "action_history": self.action_history,
            },
            path,
        )

    def load(self, path: str) -> None:
        """
        Load the recommender model, feature list, and action history.
        """
        payload = joblib.load(path)
        self.model = payload.get("model")
        self.feature_cols = payload.get("feature_cols", self.feature_cols)
        self.action_history = payload.get("action_history")
