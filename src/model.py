"""Model training, preprocessing, and serialization.

Model Architecture:
- Preprocessor: StandardScaler()
- Classifier: RandomForestClassifier(
    n_estimators=50,
    max_depth=10,
    class_weight="balanced",
    random_state=42
  )
- Persisted as: (model, scaler) via joblib
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Union

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler


def build_model() -> Tuple[RandomForestClassifier, StandardScaler]:
    """Instantiate the standard Phase 1 model and scaler."""
    scaler = StandardScaler()
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=10,
        class_weight="balanced",
        random_state=42,
    )
    return model, scaler


def fit_model(
    model: RandomForestClassifier,
    scaler: StandardScaler,
    X: np.ndarray,
    y: np.ndarray,
) -> float:
    """Fit the scaler and model, returning the internal sanity training accuracy.

    Args:
        model: RandomForestClassifier
        scaler: StandardScaler
        X: Feature matrix of shape (N, 8)
        y: Binary labels (0 = Normal, 1 = FoG)

    Returns:
        train_accuracy: Internal sanity metric (not generalization proof)
    """
    if len(X) != len(y):
        raise ValueError(f"X and y lengths mismatch: {len(X)} vs {len(y)}")

    unique_labels = np.unique(y)
    if len(unique_labels) < 2:
        raise ValueError(
            f"STOP — DEGENERATE LABELS ERROR: Training requires both classes (0 and 1). "
            f"Found classes: {unique_labels}"
        )

    X_scaled = scaler.fit_transform(X)
    model.fit(X_scaled, y)

    y_pred = model.predict(X_scaled)
    train_acc = float(accuracy_score(y, y_pred))
    return train_acc


def save_model(
    model: RandomForestClassifier,
    scaler: StandardScaler,
    model_path: Union[str, Path],
) -> str:
    """Persist (model, scaler) tuple to disk using joblib."""
    p = Path(model_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump((model, scaler), str(p))
    return str(p)


def load_model(model_path: Union[str, Path]) -> Tuple[RandomForestClassifier, StandardScaler]:
    """Load and validate (model, scaler) tuple from disk using joblib."""
    p = Path(model_path)
    if not p.exists():
        raise FileNotFoundError(f"Model artifact not found: {p}")

    loaded = joblib.load(str(p))
    if not isinstance(loaded, (tuple, list)) or len(loaded) != 2:
        raise ValueError(f"Invalid model artifact structure in {p}. Expected (model, scaler) tuple.")

    model, scaler = loaded[0], loaded[1]
    if not isinstance(model, RandomForestClassifier) or not isinstance(scaler, StandardScaler):
        raise TypeError(
            f"Expected (RandomForestClassifier, StandardScaler), got ({type(model)}, {type(scaler)})"
        )

    return model, scaler


def predict_fog_probability(
    model: RandomForestClassifier,
    scaler: StandardScaler,
    X: np.ndarray,
) -> np.ndarray:
    """Compute class-1 (FoG) probabilities for input feature matrix X of shape (N, 8).

    Returns:
        probs: 1D array of length N containing class-1 probabilities in [0.0, 1.0]
    """
    if X.ndim != 2 or X.shape[1] != 8:
        raise ValueError(f"Input feature matrix shape {X.shape} must be (N, 8)")

    X_scaled = scaler.transform(X)
    # Check if model has classes_ [0, 1]
    classes = list(model.classes_)
    if 1 not in classes:
        # If class 1 was somehow missing, probability is 0
        return np.zeros(len(X), dtype=np.float64)

    class_1_idx = classes.index(1)
    probs = model.predict_proba(X_scaled)[:, class_1_idx]
    return probs.astype(np.float64)
