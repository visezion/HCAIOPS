import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from ..data.preprocess import build_alert_training_table
from ..data.schemas import HCaiEvent
from .utils import ensure_feature_order


class _TabTransformer(nn.Module):
    def __init__(self, input_dim: int, embed_dim: int = 32, num_heads: int = 4, num_layers: int = 2) -> None:
        super().__init__()
        self.input_proj = nn.Linear(input_dim, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=num_heads, dim_feedforward=embed_dim * 2, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.head = nn.Sequential(nn.Linear(embed_dim, 32), nn.ReLU(), nn.Linear(32, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, F] -> [B, F, E]
        emb = self.input_proj(x).unsqueeze(1)
        cls = self.cls_token.expand(x.size(0), -1, -1)
        tokens = torch.cat([cls, emb], dim=1)
        enc = self.encoder(tokens)
        cls_out = enc[:, 0, :]
        return self.head(cls_out)


class _AlertDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        self.X = X
        self.y = y.astype(np.int64)

    def __len__(self) -> int:
        return len(self.y)

    def __getitem__(self, idx: int):
        return torch.tensor(self.X[idx], dtype=torch.float32), torch.tensor(self.y[idx], dtype=torch.long)


@dataclass
class AlertImportanceModel:
    """
    TabTransformer-based classifier for alert importance.
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
    model: Optional[_TabTransformer] = None
    device: str = "cpu"

    # Compatibility wrappers
    def fit_from_events(self, events: List[HCaiEvent]) -> Dict[str, float]:
        return self.train(events)

    def predict_importance(self, features: Dict[str, Any]) -> float:
        out = self.predict(features)
        return float(out.get("importance", 0.0))

    # New API
    def train(self, events: List[HCaiEvent], epochs: int = 5, batch_size: int = 32, lr: float = 1e-3) -> Dict[str, float]:
        df = build_alert_training_table(events)
        if df.empty or df[self.label_col].nunique() < 2:
            self.model = _TabTransformer(len(self.feature_cols))
            return {"precision": 0.0, "recall": 0.0, "note": "insufficient data"}

        X = ensure_feature_order(df[self.feature_cols], self.feature_cols)
        y = df[self.label_col].to_numpy()
        dataset = _AlertDataset(X, y)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self.model = _TabTransformer(len(self.feature_cols)).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        self.model.train()
        for _ in range(max(1, epochs)):
            for xb, yb in loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                logits = self.model(xb)
                loss = criterion(logits, yb)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        with torch.no_grad():
            logits = self.model(torch.tensor(X, dtype=torch.float32))
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            precision = float((preds == y).mean())
        return {"precision": precision, "recall": precision, "note": "trained"}

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None:
            self.model = _TabTransformer(len(self.feature_cols))
        x = np.array([[features.get(col, 0.0) for col in self.feature_cols]], dtype=np.float32)
        with torch.no_grad():
            logits = self.model(torch.tensor(x, dtype=torch.float32))
            probs = torch.softmax(logits, dim=1)
            prob1 = float(probs[0, 1].item())
            pred_class = int(torch.argmax(probs, dim=1).item())
        return {"importance": prob1, "class": str(pred_class)}

    def save(self, path: str) -> None:
        target_path = Path(path)
        if target_path.suffix != ".pt":
            target_path = target_path.with_suffix(".pt")
        payload = {
            "state_dict": self.model.state_dict() if self.model else None,
            "feature_cols": list(self.feature_cols),
            "label_col": self.label_col,
        }
        torch.save(payload, target_path)

    def load(self, path: str) -> None:
        try:
            payload = torch.load(path, map_location="cpu", weights_only=False)
        except Exception:
            payload = torch.load(path, map_location="cpu")
        self.feature_cols = payload.get("feature_cols", self.feature_cols)
        self.label_col = payload.get("label_col", self.label_col)
        self.model = _TabTransformer(len(self.feature_cols))
        state = payload.get("state_dict")
        if state:
            self.model.load_state_dict(state)
        self.model.to(self.device)
