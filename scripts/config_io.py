#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path
from typing import Any

import sys

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for direct script execution without installed deps
    vendor = Path(__file__).resolve().parent / "_vendor"
    if vendor.exists():
        sys.path.insert(0, str(vendor))
        import yaml  # type: ignore
    else:
        raise


def load_config(path: Path) -> dict[str, Any]:
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"Configuration files must be YAML (.yaml/.yml): {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML config must contain an object at top level: {path}")
    return data
