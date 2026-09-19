"""Canonical JSON Contract definition and validation.

Baseline schema:
[
  {
    "start": 5.2,
    "end": 6.8,
    "confidence": 0.92,
    "type": "FoG",
    "primary_cue": "left_ankle_velocity",
    "data_mode": "real"
  }
]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from src.features import CANONICAL_FEATURES

VALID_TYPES = {"FoG", "Borderline", "Normal"}
VALID_DATA_MODES = {"real", "synthetic_demo"}


def validate_episode_dict(item: Dict[str, Any]) -> None:
    """Validate that a single episode dictionary strictly matches the canonical schema."""
    required_keys = {"start", "end", "confidence", "type", "primary_cue", "data_mode"}
    missing = required_keys - set(item.keys())
    if missing:
        raise ValueError(f"Canonical JSON episode missing required keys: {missing} in {item}")

    # Start and End
    if not isinstance(item["start"], (int, float)) or item["start"] < 0:
        raise ValueError(f"Invalid 'start' timestamp: {item['start']}")
    if not isinstance(item["end"], (int, float)) or item["end"] < item["start"]:
        raise ValueError(f"Invalid 'end' timestamp ({item['end']}) relative to start ({item['start']})")

    # Confidence
    conf = item["confidence"]
    if not isinstance(conf, (int, float)) or conf < 0.0 or conf > 1.0:
        raise ValueError(f"Invalid 'confidence' value: {conf} (must be between 0.0 and 1.0)")

    # Type
    t = item["type"]
    if t not in VALID_TYPES:
        raise ValueError(f"Invalid episode 'type': {t}. Must be one of {VALID_TYPES}")

    # Primary cue
    cue = item["primary_cue"]
    if cue not in CANONICAL_FEATURES:
        raise ValueError(f"Invalid 'primary_cue': {cue}. Must be one of {CANONICAL_FEATURES}")

    # Data mode
    mode = item["data_mode"]
    if mode not in VALID_DATA_MODES:
        raise ValueError(f"Invalid 'data_mode': {mode}. Must be one of {VALID_DATA_MODES}")


def format_episodes_json(episodes: List[Any], indent: int = 2) -> str:
    """Format a list of Episode objects or dicts into canonical JSON string."""
    dict_list: List[Dict[str, Any]] = []
    for ep in episodes:
        d = ep.to_dict() if hasattr(ep, "to_dict") else dict(ep)
        validate_episode_dict(d)
        dict_list.append(d)

    return json.dumps(dict_list, indent=indent)


def save_canonical_json(episodes: List[Any], output_path: Union[str, Path]) -> str:
    """Validate and write episodes to canonical JSON file."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    json_str = format_episodes_json(episodes)
    with open(p, "w", encoding="utf-8") as f:
        f.write(json_str)
    return str(p)


def load_and_validate_canonical_json(json_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load JSON from disk and assert that every entry satisfies the canonical schema."""
    p = Path(json_path)
    if not p.exists():
        raise FileNotFoundError(f"JSON file not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Root of canonical JSON must be a list of episode objects, got {type(data)}")

    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Each entry in JSON must be an object, got {type(item)}")
        validate_episode_dict(item)

    return data
