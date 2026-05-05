from __future__ import annotations

from pathlib import Path

from pytest_bdd import scenarios


ROOT = Path(__file__).resolve().parents[2]
scenarios(str(ROOT / "features"))
