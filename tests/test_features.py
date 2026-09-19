"""Unit tests for the canonical 8-feature contract."""

import numpy as np
import pandas as pd
import pytest

from src.features import CANONICAL_FEATURES, extract_feature_matrix, get_canonical_feature_names


def test_canonical_feature_names_and_ordering():
    """Verify that the 8 canonical features match the required immutable order."""
    expected = [
        "left_ankle_velocity",
        "right_ankle_velocity",
        "left_knee_angle",
        "right_knee_angle",
        "stride_width",
        "accel_rms",
        "gyro_x_var",
        "gyro_z_var",
    ]
    assert list(CANONICAL_FEATURES) == expected
    assert get_canonical_feature_names() == expected


def test_extract_feature_matrix_shape_and_ordering(sample_fused_df):
    """Verify extracted matrix shape (N, 8) and exact feature alignment."""
    # Permute columns to test that extract_feature_matrix re-orders strictly
    permuted_df = sample_fused_df[
        ["gyro_z_var", "stride_width", "left_ankle_velocity"] +
        [c for c in sample_fused_df.columns if c not in ["gyro_z_var", "stride_width", "left_ankle_velocity"]]
    ]

    X = extract_feature_matrix(permuted_df)
    assert X.shape == (len(sample_fused_df), 8)

    # First column must be left_ankle_velocity
    assert np.allclose(X[:, 0], sample_fused_df["left_ankle_velocity"].to_numpy())
    # Last column must be gyro_z_var
    assert np.allclose(X[:, 7], sample_fused_df["gyro_z_var"].to_numpy())


def test_extract_feature_matrix_missing_feature(sample_fused_df):
    """Missing any of the 8 canonical features must raise ValueError."""
    bad_df = sample_fused_df.drop(columns=["accel_rms"])
    with pytest.raises(ValueError, match="DataFrame is missing canonical features"):
        extract_feature_matrix(bad_df)


def test_extract_feature_matrix_rejects_nans(sample_fused_df):
    """NaNs in feature matrix must raise ValueError."""
    bad_df = sample_fused_df.copy()
    bad_df.loc[0, "stride_width"] = np.nan
    with pytest.raises(ValueError, match="contains NaN values"):
        extract_feature_matrix(bad_df)
