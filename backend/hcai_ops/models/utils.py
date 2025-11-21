from typing import Dict, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split


def split_dataset(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
    label_col: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Split a DataFrame into train and test numpy arrays.
    Returns X_train, X_test, y_train, y_test.
    """
    features = ensure_feature_order(df, feature_cols)
    labels = df[label_col].to_numpy()
    return train_test_split(features, labels, test_size=test_size, random_state=random_state, stratify=labels)


def evaluate_classification(
    y_true,
    y_pred,
) -> Dict[str, float]:
    """
    Compute accuracy, precision, recall, and f1 score (binary).
    Return a dict with keys: accuracy, precision, recall, f1.
    """
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def ensure_feature_order(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
) -> np.ndarray:
    """
    Return features as numpy array in a fixed column order.
    """
    ordered = df.reindex(columns=feature_cols, fill_value=np.nan)
    return ordered.to_numpy()
