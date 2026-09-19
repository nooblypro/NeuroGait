"""Canonical 8-Feature Contract and Matrix Extraction.

The model input MUST contain exactly these 8 features in this immutable order:
1. left_ankle_velocity
2. right_ankle_velocity
3. left_knee_angle
4. right_knee_angle
5. stride_width
6. accel_rms
7. gyro_x_var
8. gyro_z_var

Shape: (N, 8)
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

CANONICAL_FEATURES: Tuple[str, ...] = (
    "left_ankle_velocity",
    "right_ankle_velocity",
    "left_knee_angle",
    "right_knee_angle",
    "stride_width",
    "accel_rms",
    "gyro_x_var",
    "gyro_z_var",
)


def get_canonical_feature_names() -> List[str]:
    """Return a copy of the canonical feature names in immutable order."""
    return list(CANONICAL_FEATURES)


def extract_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Extract and validate the (N, 8) canonical feature matrix from a fused DataFrame.

    Enforces:
    - Presence of all 8 features
    - Immutable ordering
    - Shape (N, 8)
    - Absence of NaN or Inf values

    Returns:
        X: np.ndarray of shape (N, 8) with dtype float64
    """
    missing = [f for f in CANONICAL_FEATURES if f not in df.columns]
    if missing:
        raise ValueError(
            f"DataFrame is missing canonical features: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    # Strictly reorder columns according to canonical contract
    sub_df = df[list(CANONICAL_FEATURES)].copy()

    X = sub_df.to_numpy(dtype=np.float64)

    if X.ndim != 2 or X.shape[1] != len(CANONICAL_FEATURES):
        raise ValueError(
            f"Feature matrix has invalid shape {X.shape}, expected (N, {len(CANONICAL_FEATURES)})"
        )

    if np.isnan(X).any():
        raise ValueError("Canonical feature matrix contains NaN values after extraction.")

    if np.isinf(X).any():
        raise ValueError("Canonical feature matrix contains Inf values after extraction.")

    return X
