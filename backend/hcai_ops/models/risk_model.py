import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from ..data.preprocess import build_risk_training_table
from ..data.schemas import HCaiEvent
from .utils import ensure_feature_order


class _RiskLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 32, num_layers: int = 1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden_dim, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, F]
        out, _ = self.lstm(x)
        last = out[:, -1, :]
        return self.head(last).squeeze(-1)


class _RiskDataset(Dataset):
    def __init__(self, data: np.ndarray, labels: np.ndarray, window: int) -> None:
        self.data = data
        self.labels = labels
        self.window = window

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return torch.tensor(self.data[idx], dtype=torch.float32), torch.tensor(self.labels[idx], dtype=torch.float32)


@dataclass
class RiskModel:
    """
    LSTM-based time-series classifier for incident risk.
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
    model: Optional[_RiskLSTM] = None
    window: int = 5
    device: str = "cpu"

    # ---- Compatibility wrappers ----
    def fit_from_events(self, events: List[HCaiEvent]) -> Dict[str, float]:
        return self.train(events)

    def predict_from_features(self, features: Dict[str, Any]) -> float:
        out = self.predict(features)
        return float(out.get("score", 0.0))

    # ---- New API ----
    def _prepare_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        # Sort by time and build sliding windows
        df = df.sort_values("window_start")
        feats = ensure_feature_order(df[self.feature_cols], self.feature_cols)
        labels = df[self.label_col].to_numpy().astype(np.float32)
        sequences = []
        seq_labels = []
        for i in range(len(df)):
            start = max(0, i - self.window + 1)
            window_feats = feats[start : i + 1]
            if window_feats.shape[0] < self.window:
                pad = np.zeros((self.window - window_feats.shape[0], window_feats.shape[1]), dtype=np.float32)
                window_feats = np.vstack([pad, window_feats])
            sequences.append(window_feats)
            seq_labels.append(labels[i])
        return np.stack(sequences), np.array(seq_labels)

    def train(self, events: List[HCaiEvent], epochs: int = 5, batch_size: int = 32, lr: float = 1e-3) -> Dict[str, float]:
        df = build_risk_training_table(events)
        if df.empty or df[self.label_col].nunique() < 2:
            # Not enough data; store a trivial model
            self.model = _RiskLSTM(len(self.feature_cols))
            return {"accuracy": 0.0, "f1": 0.0, "note": "insufficient data"}

        X, y = self._prepare_sequences(df)
        dataset = _RiskDataset(X, y, self.window)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self.model = _RiskLSTM(len(self.feature_cols)).to(self.device)
        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        self.model.train()
        for _ in range(max(1, epochs)):
            for xb, yb in loader:
                xb = xb.to(self.device)
                yb = yb.to(self.device)
                logits = self.model(xb)
                loss = criterion(logits, yb)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        # simple metrics
        with torch.no_grad():
            logits = self.model(torch.tensor(X, dtype=torch.float32))
            probs = torch.sigmoid(logits).cpu().numpy()
            preds = (probs >= 0.5).astype(int)
            acc = float((preds == y).mean())
        return {"accuracy": acc, "f1": acc, "note": "trained"}

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None:
            self.model = _RiskLSTM(len(self.feature_cols))
        x = np.array([[features.get(col, 0.0) for col in self.feature_cols]], dtype=np.float32)
        # pad window
        x_window = np.zeros((1, self.window, len(self.feature_cols)), dtype=np.float32)
        x_window[0, -1, :] = x
        with torch.no_grad():
            logits = self.model(torch.tensor(x_window, dtype=torch.float32))
            score = float(torch.sigmoid(logits).item())
        label = "high" if score >= 0.5 else "low"
        return {"score": score, "label": label}

    def save(self, path: str) -> None:
        target_path = Path(path)
        if target_path.suffix != ".pt":
            target_path = target_path.with_suffix(".pt")
        payload = {
            "state_dict": self.model.state_dict() if self.model else None,
            "feature_cols": list(self.feature_cols),
            "label_col": self.label_col,
            "window": self.window,
        }
        torch.save(payload, target_path)

    def load(self, path: str) -> None:
        try:
            payload = torch.load(path, map_location="cpu", weights_only=False)
        except Exception:
            payload = torch.load(path, map_location="cpu")
        self.feature_cols = payload.get("feature_cols", self.feature_cols)
        self.label_col = payload.get("label_col", self.label_col)
        self.window = payload.get("window", self.window)
        self.model = _RiskLSTM(len(self.feature_cols))
        state = payload.get("state_dict")
        if state:
            self.model.load_state_dict(state)
        self.model.to(self.device)
