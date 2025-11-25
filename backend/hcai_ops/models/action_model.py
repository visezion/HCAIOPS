import random
from pathlib import Path
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from ..data.preprocess import build_action_training_table
from ..data.schemas import HCaiEvent
from .utils import ensure_feature_order


class _DQNetwork(nn.Module):
    def __init__(self, input_dim: int, action_dim: int = 10) -> None:
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


class _ReplayBuffer:
    def __init__(self, capacity: int = 1000) -> None:
        self.buffer: Deque[Tuple[np.ndarray, int, float, np.ndarray]] = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray) -> None:
        self.buffer.append((state, action, reward, next_state))

    def sample(self, batch_size: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        states, actions, rewards, next_states = zip(*batch)
        return (
            np.stack(states),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.stack(next_states),
        )

    def __len__(self) -> int:
        return len(self.buffer)


@dataclass
class ActionRecommender:
    """
    DQN-based recommender for operator actions.
    """

    feature_cols: Sequence[str] = field(default_factory=lambda: ["cpu_before", "error_rate_before"])
    model: Optional[_DQNetwork] = None
    action_space: List[str] = field(default_factory=list)
    replay: _ReplayBuffer = field(default_factory=lambda: _ReplayBuffer(2000))
    device: str = "cpu"

    # Compatibility wrappers
    def fit_from_events(self, events: List[HCaiEvent]) -> None:
        self.train(events)

    def recommend_action(self, context_features: Dict[str, Any]) -> Optional[str]:
        out = self.recommend(context_features)
        return out.get("action")

    # New API
    def _encode_actions(self, actions: List[str]) -> None:
        unique = sorted({a for a in actions if a})
        self.action_space = unique or ["noop"]

    def train(
        self,
        events: List[HCaiEvent],
        episodes: int = 10,
        batch_size: int = 32,
        gamma: float = 0.9,
        lr: float = 1e-3,
        epsilon_start: float = 0.1,
        epsilon_end: float = 0.01,
    ) -> Dict[str, Any]:
        df = build_action_training_table(events)
        if df.empty or "applied_action" not in df.columns:
            self.model = _DQNetwork(len(self.feature_cols), action_dim=1)
            self.action_space = ["noop"]
            self.action_history = None
            return {"status": "ok", "note": "insufficient data"}

        # Encode actions
        actions = df["applied_action"].fillna("noop").astype(str).tolist()
        self._encode_actions(actions)
        action_dim = len(self.action_space)

        features = ensure_feature_order(df[self.feature_cols], self.feature_cols)
        rewards = np.ones(len(df), dtype=np.float32)  # simple positive reward for observed actions

        self.model = _DQNetwork(len(self.feature_cols), action_dim=action_dim).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        epsilon = epsilon_start
        epsilon_decay = (epsilon_start - epsilon_end) / max(1, episodes)

        for _ in range(max(1, episodes)):
            for feat, action, reward in zip(features, actions, rewards):
                state = feat.astype(np.float32)
                action_idx = self.action_space.index(action)
                # simple next state = same state (no environment), reward static
                next_state = state.copy()
                self.replay.push(state, action_idx, reward, next_state)

                if len(self.replay) >= batch_size:
                    s_batch, a_batch, r_batch, ns_batch = self.replay.sample(batch_size)
                    s_t = torch.tensor(s_batch, dtype=torch.float32, device=self.device)
                    ns_t = torch.tensor(ns_batch, dtype=torch.float32, device=self.device)
                    a_t = torch.tensor(a_batch, dtype=torch.long, device=self.device)
                    r_t = torch.tensor(r_batch, dtype=torch.float32, device=self.device)

                    q_values = self.model(s_t)
                    q_action = q_values.gather(1, a_t.unsqueeze(1)).squeeze(1)

                    with torch.no_grad():
                        next_q = self.model(ns_t).max(1)[0]
                        target = r_t + gamma * next_q

                    loss = criterion(q_action, target)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

            epsilon = max(epsilon_end, epsilon - epsilon_decay)

        self.action_history = df.reset_index(drop=True)
        return {"status": "ok", "actions": len(self.action_space)}

    def recommend(self, context_features: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None:
            # default model if not trained
            self.model = _DQNetwork(len(self.feature_cols), action_dim=len(self.action_space) or 1)
            if not self.action_space:
                self.action_space = ["noop"]
        x = np.array([[context_features.get(col, 0.0) for col in self.feature_cols]], dtype=np.float32)
        with torch.no_grad():
            q_values = self.model(torch.tensor(x, dtype=torch.float32))
            best_idx = int(torch.argmax(q_values, dim=1).item())
            best_q = float(q_values[0, best_idx].item())
        action = self.action_space[best_idx] if self.action_space else "noop"
        confidence = float(torch.sigmoid(torch.tensor(best_q)).item())
        return {"action": action, "confidence": confidence}

    def save(self, path: str) -> None:
        target_path = Path(path)
        if target_path.suffix != ".pt":
            target_path = target_path.with_suffix(".pt")
        payload = {
            "state_dict": self.model.state_dict() if self.model else None,
            "feature_cols": list(self.feature_cols),
            "action_space": self.action_space,
            "action_history": self.action_history,
        }
        torch.save(payload, target_path)

    def load(self, path: str) -> None:
        try:
            payload = torch.load(path, map_location="cpu", weights_only=False)
        except Exception:
            payload = torch.load(path, map_location="cpu")
        self.feature_cols = payload.get("feature_cols", self.feature_cols)
        self.action_space = payload.get("action_space", self.action_space)
        self.action_history = payload.get("action_history", None)
        action_dim = max(1, len(self.action_space))
        self.model = _DQNetwork(len(self.feature_cols), action_dim=action_dim)
        state = payload.get("state_dict")
        if state:
            self.model.load_state_dict(state)
        self.model.to(self.device)
