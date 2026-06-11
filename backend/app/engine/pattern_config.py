"""Load pattern definitions from pattern_definition.yaml (single source of truth)."""

from pathlib import Path
import yaml

_yaml_path = Path(__file__).parent.parent.parent.parent / "pattern_definition.yaml"

with open(_yaml_path, "r", encoding="utf-8") as f:
    _data = yaml.safe_load(f)

PATTERNS: list[dict] = _data["patterns"]

# Lookup helpers
PATTERN_NAMES: list[str] = [p["name"] for p in PATTERNS]
LABEL_MAP: dict[str, str] = {p["name"]: p["label"] for p in PATTERNS}
NAME_MAP: dict[str, str] = {p["label"]: p["name"] for p in PATTERNS}
MODULE_MAP: dict[str, str] = {p["name"]: p["module"] for p in PATTERNS}
MARKET_DEPENDENT: set[str] = {p["name"] for p in PATTERNS if p["market_dependent"]}
NON_MARKET: set[str] = {p["name"] for p in PATTERNS if not p["market_dependent"]}
DEFAULT_CONFIDENCE: dict[str, float] = {p["name"]: p["confidence"] for p in PATTERNS}


def label(name: str) -> str:
    """Get Chinese label for a pattern name."""
    return LABEL_MAP.get(name, name)


def name(label_str: str) -> str:
    """Get pattern name from Chinese label."""
    return NAME_MAP.get(label_str, label_str)
