"""
TieBreaker Model Evaluation - compatibility shim.

This is a thin wrapper around the canonical in-package implementation at
``backend/app/ml/evaluation.py``.  Running ``python ml/evaluation.py`` from the
repo root delegates to ``app.ml.evaluation.main`` so the legacy entry point
keeps working.
"""
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `import app.ml.evaluation` resolves.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.evaluation import main  # noqa: E402

if __name__ == "__main__":
    main()

