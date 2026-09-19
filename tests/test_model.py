"""Unit tests for model training, validation, and persistence."""

from pathlib import Path
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from src.model import build_model, fit_model, load_model, predict_fog_probability, save_model


def test_build_model_hyperparameters():
    """Verify RandomForest hyperparameters per Section 8 specification."""
    model, scaler = build_model()
    assert isinstance(model, RandomForestClassifier)
    assert isinstance(scaler, StandardScaler)
    assert model.n_estimators == 50
    assert model.max_depth == 10
    assert model.class_weight == "balanced"
    assert model.random_state == 42


def test_fit_and_predict_probability():
    """Fit model on synthetic data and verify class-1 probabilities in [0, 1]."""
    model, scaler = build_model()
    # 40 samples, 8 features
    X = np.random.randn(40, 8)
    y = np.array([0] * 20 + [1] * 20)

    train_acc = fit_model(model, scaler, X, y)
    assert 0.0 <= train_acc <= 1.0

    probs = predict_fog_probability(model, scaler, X)
    assert probs.shape == (40,)
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)


def test_degenerate_labels_error():
    """STOP — DEGENERATE LABELS ERROR when labels contain only one class."""
    model, scaler = build_model()
    X = np.random.randn(20, 8)
    y_single_class = np.zeros(20, dtype=int)

    with pytest.raises(ValueError, match="STOP — DEGENERATE LABELS ERROR"):
        fit_model(model, scaler, X, y_single_class)


def test_model_persistence_roundtrip(tmp_path):
    """Save model to disk, reload, and verify identical probability outputs."""
    model, scaler = build_model()
    X = np.random.randn(30, 8)
    y = np.array([0] * 15 + [1] * 15)
    fit_model(model, scaler, X, y)

    orig_probs = predict_fog_probability(model, scaler, X)

    artifact_path = tmp_path / "test_fog_model.pkl"
    save_model(model, scaler, artifact_path)
    assert artifact_path.exists()

    loaded_model, loaded_scaler = load_model(artifact_path)
    loaded_probs = predict_fog_probability(loaded_model, loaded_scaler, X)

    assert np.allclose(orig_probs, loaded_probs)
