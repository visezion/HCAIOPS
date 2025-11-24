"""
Generic training helper for tabular data stored in Excel.

Usage examples (run from repo root with the venv active):
  python backend/scripts/train_from_excel.py \
    --input data/Haftalık_iş_rapor_230807_0814.xlsx \
    --sheet Şubat \
    --target failed

  python backend/scripts/train_from_excel.py --input data/Haftalık_iş_rapor_230807_0814.xlsx --sheet List --target failed
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate, train_test_split


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a quick model from an Excel sheet.")
    parser.add_argument("--input", type=Path, required=True, help="Path to the Excel file")
    parser.add_argument("--sheet", type=str, default=None, help="Sheet name (defaults to first sheet)")
    parser.add_argument("--target", type=str, required=True, help="Column to predict")
    parser.add_argument(
        "--model-out",
        type=Path,
        default=Path("models_store") / "excel_model.pkl",
        help="Where to write the fitted model",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="Holdout fraction")
    parser.add_argument("--sample-rows", type=int, default=None, help="Optional row cap to subsample large CSV/Excel files")
    parser.add_argument("--drop-cols", type=str, default="", help="Comma-separated columns to drop explicitly")
    parser.add_argument(
        "--drop-patterns",
        type=str,
        default="id,time,index,collection",
        help="Comma-separated substrings; any column containing one will be dropped (case-insensitive).",
    )
    parser.add_argument("--time-split-col", type=str, default=None, help="Column name to use for time-based split (train on earlier, test on later)")
    parser.add_argument("--time-split-ratio", type=float, default=0.8, help="Fraction of data (by time) for training if time-split-col is set")
    parser.add_argument("--class-weight", type=str, default=None, choices=[None, "balanced"], help="Class weight for classification models")
    return parser.parse_args()


def _safe_literal(val: Any) -> Any:
    if isinstance(val, (dict, list, tuple)):
        return val
    if not isinstance(val, str):
        return val
    stripped = val.strip()
    if not stripped:
        return np.nan
    # Only attempt structured parse if it looks like JSON-ish content.
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return ast.literal_eval(stripped)
        except Exception:
            try:
                return json.loads(stripped)
            except Exception:
                return val
    return val


def _flatten_dict(prefix: str, obj: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in obj.items():
        try:
            out[f"{prefix}_{k}"] = float(v)
        except Exception:
            continue
    return out


def _stats_from_iterable(prefix: str, values: Iterable[Any]) -> dict[str, float]:
    nums = []
    for v in values:
        try:
            nums.append(float(v))
        except Exception:
            continue
    if not nums:
        return {}
    arr = np.array(nums, dtype=float)
    return {
        f"{prefix}_mean": float(np.mean(arr)),
        f"{prefix}_min": float(np.min(arr)),
        f"{prefix}_max": float(np.max(arr)),
        f"{prefix}_p90": float(np.percentile(arr, 90)),
        f"{prefix}_p99": float(np.percentile(arr, 99)),
    }


def load_dataframe(path: Path, sheet: str | None, sample_rows: int | None) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        print(f"Loading CSV {path} (sample_rows={sample_rows})")
        return pd.read_csv(path, nrows=sample_rows)
    xl = pd.ExcelFile(path)
    sheet_to_use = sheet or xl.sheet_names[0]
    print(f"Loading sheet '{sheet_to_use}' from {path} (sample_rows={sample_rows})")
    df = xl.parse(sheet_to_use, nrows=sample_rows)
    return df


def build_features(
    df: pd.DataFrame, target: str, drop_cols: list[str], drop_patterns: list[str]
) -> tuple[pd.DataFrame, pd.Series]:
    if target not in df.columns:
        raise SystemExit(f"Target column '{target}' not found. Available: {list(df.columns)}")

    # Drop explicit columns if requested.
    for col in drop_cols:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Drop pattern-matching columns (except the target).
    def matches_pattern(col: str) -> bool:
        c = col.lower()
        return any(pat in c for pat in drop_patterns)

    for col in list(df.columns):
        if col == target:
            continue
        if matches_pattern(col):
            df = df.drop(columns=[col])

    y = df[target]
    df = df.drop(columns=[target])

    # Keep track of derived features.
    derived: dict[str, list[float]] = {}

    def add_feature(name: str, values: list[float]) -> None:
        derived[name] = values

    # Process columns
    for col in list(df.columns):
        series = df[col]
        if series.dtype.kind in {"i", "u", "f", "b"}:
            continue  # already numeric
        # Attempt numeric coercion first
        coerced = pd.to_numeric(series, errors="coerce")
        if coerced.notna().any():
            df[col] = coerced
            continue

        # Try parsing literals only if the strings look structured
        parsed = series.map(_safe_literal)

        if parsed.apply(lambda v: isinstance(v, Mapping)).any():
            rows = []
            for v in parsed:
                rows.append(_flatten_dict(col, v) if isinstance(v, Mapping) else {})
            if rows:
                keys = sorted({k for row in rows for k in row})
                for k in keys:
                    add_feature(k, [row.get(k, np.nan) for row in rows])
            df = df.drop(columns=[col])
            continue

        if parsed.apply(lambda v: isinstance(v, (list, tuple))).any():
            stats = [_stats_from_iterable(col, v) if isinstance(v, (list, tuple)) else {} for v in parsed]
            keys = sorted({k for row in stats for k in row})
            for k in keys:
                add_feature(k, [row.get(k, np.nan) for row in stats])
            df = df.drop(columns=[col])
            continue

        # Fallback: drop non-numeric text columns
        df = df.drop(columns=[col])

    if derived:
        for name, values in derived.items():
            df[name] = values

    # Drop completely empty columns
    df = df.dropna(axis=1, how="all")
    # Fill remaining NaN with median (robust for skewed data)
    df = df.fillna(df.median(numeric_only=True))
    # Keep only numeric columns
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        raise SystemExit("No numeric features found after processing.")

    y_numeric = pd.to_numeric(y, errors="coerce")
    if not y_numeric.isna().all():
        # If we got some numeric values, fill remaining NaN with mode or 0
        if y_numeric.isna().any():
            mode_vals = y_numeric.mode()
            fill_val = mode_vals.iloc[0] if not mode_vals.empty else 0
            y_numeric = y_numeric.fillna(fill_val)
        y = y_numeric

    return numeric_df, y


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    drop_cols = [c.strip() for c in args.drop_cols.split(",") if c.strip()]
    drop_patterns = [p.strip().lower() for p in args.drop_patterns.split(",") if p.strip()]

    df = load_dataframe(args.input, args.sheet, args.sample_rows)
    print(f"Loaded data shape: {df.shape}")
    X, y = build_features(df, args.target, drop_cols, drop_patterns)
    print(f"Features: {X.shape[1]} cols, Records: {X.shape[0]}")

    # Decide task type
    is_classification = (y.dtype == object) or (hasattr(y, "nunique") and y.nunique() <= 20)

    # Time-based split if requested
    if args.time_split_col and args.time_split_col in df.columns:
        time_col = args.time_split_col
        # Append target back temporarily to align with original rows
        tmp = X.copy()
        tmp[time_col] = df[time_col].values
        tmp[args.target] = y.values
        tmp_sorted = tmp.sort_values(time_col)
        split_idx = int(len(tmp_sorted) * args.time_split_ratio)
        train_df = tmp_sorted.iloc[:split_idx]
        test_df = tmp_sorted.iloc[split_idx:]
        X_train = train_df.drop(columns=[time_col, args.target])
        y_train = train_df[args.target]
        X_test = test_df.drop(columns=[time_col, args.target])
        y_test = test_df[args.target]
        print(f"Time-based split on '{time_col}' with ratio {args.time_split_ratio}: train={len(train_df)}, test={len(test_df)}")
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, stratify=y if is_classification else None, random_state=42
        )

    if is_classification:
        model = RandomForestClassifier(
            n_estimators=300, n_jobs=-1, random_state=42, class_weight=args.class_weight
        )
    else:
        model = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42)

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    # Cross-validation for a more realistic score.
    if is_classification:
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        scoring = {"accuracy": "accuracy", "f1_macro": "f1_macro"}
    else:
        cv = KFold(n_splits=3, shuffle=True, random_state=42)
        scoring = {"r2": "r2", "rmse": "neg_root_mean_squared_error"}

    print("Running 3-fold cross validation...")
    cv_results = cross_validate(model, X, y, cv=cv, scoring=scoring, n_jobs=-1, error_score="raise")
    for metric, values in cv_results.items():
        if not metric.startswith("test_"):
            continue
        scores = values
        metric_name = metric.replace("test_", "")
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        # For neg_root_mean_squared_error, invert sign
        if metric_name == "rmse":
            mean_score = -mean_score
            std_score = np.std([-v for v in scores])
        print(f"  CV {metric_name}: {mean_score:.4f} +/- {std_score:.4f}")

    if is_classification:
        print("Classification report:")
        print(classification_report(y_test, preds))
    else:
        print("Regression metrics:")
        print("  MAE:", mean_absolute_error(y_test, preds))
        print("  RMSE:", mean_squared_error(y_test, preds, squared=False))
        print("  R2:", r2_score(y_test, preds))

    # Baseline and shuffle sanity checks
    if is_classification:
        majority = y_train.mode().iloc[0]
        y_base = np.array([majority] * len(y_test))
        base_acc = accuracy_score(y_test, y_base)
        base_f1 = f1_score(y_test, y_base, average="macro", zero_division=0)
        print(f"Baseline (majority={majority}): accuracy={base_acc:.4f}, f1_macro={base_f1:.4f}")

        y_shuffled = y.sample(frac=1, random_state=42).reset_index(drop=True)
        shuff_results = cross_validate(model, X, y_shuffled, cv=cv, scoring=scoring, n_jobs=-1, error_score="raise")
        for metric, values in shuff_results.items():
            if not metric.startswith("test_"):
                continue
            scores = values
            metric_name = metric.replace("test_", "")
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            if metric_name == "rmse":
                mean_score = -mean_score
                std_score = np.std([-v for v in scores])
            print(f"Shuffled target CV {metric_name}: {mean_score:.4f} +/- {std_score:.4f}")
    else:
        mean_pred = float(np.mean(y_train))
        base_preds = np.array([mean_pred] * len(y_test))
        base_mae = mean_absolute_error(y_test, base_preds)
        base_rmse = mean_squared_error(y_test, base_preds, squared=False)
        base_r2 = r2_score(y_test, base_preds)
        print(f"Baseline (mean): MAE={base_mae:.4f}, RMSE={base_rmse:.4f}, R2={base_r2:.4f}")

    # Feature importances
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        top_idx = np.argsort(importances)[::-1][:15]
        print("Top features:")
        for idx in top_idx:
            print(f"  {X.columns[idx]}: {importances[idx]:.4f}")

    # Threshold sweep (classification only, if probabilities available)
    if is_classification and hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X_test)[:, 1]
            thresholds = [0.3, 0.5, 0.7]
            print("Threshold sweep (positive class=1):")
            for t in thresholds:
                y_hat = (proba >= t).astype(int)
                prec = precision_score(y_test, y_hat, zero_division=0)
                rec = recall_score(y_test, y_hat, zero_division=0)
                f1 = f1_score(y_test, y_hat, zero_division=0)
                print(f"  threshold={t:.2f}: precision={prec:.3f}, recall={rec:.3f}, f1={f1:.3f}")
        except Exception:
            pass

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": list(X.columns)}, args.model_out)
    print(f"Saved model to {args.model_out}")


if __name__ == "__main__":
    main()
