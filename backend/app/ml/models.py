import hashlib
import logging
from pathlib import Path

import joblib

from .data import FRAUD_FEATURES, FP_FEATURES

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

# Feature lists are imported from data.py (single source of truth).
# The artifact's own ``features`` key always takes precedence at load time.

try:
    from sklearn.ensemble import GradientBoostingClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


def _verify_sha256(path: Path) -> bool:
    """Verify artifact integrity against its SHA-256 sidecar file."""
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.exists():
        logger.warning(f"SHA-256 sidecar missing for {path}")
        return False
    expected = sidecar.read_text().strip()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    return expected == actual


def _extract_features(record: dict, features: list) -> list:
    """Extract ordered feature values from a raw record dict."""
    return [record.get(f, 0.0) for f in features]


class ModelManager:
    """Lazy-loading model manager that falls back to rule-based heuristics
    when ML artifacts are missing or fail to load.
    """

    def __init__(self):
        self.fraud_model = None
        self.fp_model = None
        self.fraud_features = FRAUD_FEATURES
        self.fp_features = FP_FEATURES
        self.fraud_threshold = 0.5
        self.fp_threshold = 0.5
        self.fraud_metrics = {}
        self.fp_metrics = {}
        self._version_info = {"version": "unloaded"}
        self._load_models()

    def _load_models(self):
        if not SKLEARN_AVAILABLE and not XGBOOST_AVAILABLE:
            logger.warning("Neither sklearn nor xgboost available; using heuristic fallback")
            return

        paths = {
            "fraud": (ARTIFACTS_DIR / "fraud_model.joblib", FRAUD_FEATURES, self.fraud_metrics),
            "fp": (ARTIFACTS_DIR / "fp_model.joblib", FP_FEATURES, self.fp_metrics),
        }
        for name, (path, feats, default_metrics) in paths.items():
            if path.exists():
                try:
                    if not _verify_sha256(path):
                        logger.error(f"SHA-256 mismatch for {path}; using heuristic fallback")
                        continue
                    data = joblib.load(path)
                    setattr(self, f"{name}_model", data["model"])
                    setattr(self, f"{name}_features", data.get("features", feats))
                    setattr(self, f"{name}_threshold", data.get("threshold", 0.5))
                    setattr(self, f"{name}_metrics", data.get("metrics", default_metrics))
                    self._version_info = {
                        "version": data.get("version", "unknown"),
                        "best_params": data.get("best_params", {}),
                    }
                    logger.info(f"Loaded {name} model from {path} (version={data.get('version', 'unknown')})")
                except Exception as e:
                    logger.warning(f"Failed to load {name} model: {e}")
            else:
                logger.warning(f"{name} model artifact not found at {path}")

    # ------------------------------------------------------------------
    # Version info
    # ------------------------------------------------------------------
    def current_version_info(self) -> dict:
        return {
            **self._version_info,
            "fraud_threshold": self.fraud_threshold,
            "fp_threshold": self.fp_threshold,
        }

    def get_shap_drivers(self, record: dict, top_n: int = 3) -> list:
        try:
            import shap
            if self.fraud_model is None:
                raise RuntimeError("Fraud model not loaded")

            # Handle CalibratedClassifierCV wrapper
            model_for_shap = self.fraud_model
            if hasattr(model_for_shap, "calibrated_classifiers_"):
                model_for_shap = model_for_shap.calibrated_classifiers_[0].estimator

            explainer = shap.TreeExplainer(model_for_shap)
            features = _extract_features(record, self.fraud_features)
            sv = explainer.shap_values([features])
            if isinstance(sv, list):
                sv = sv[1][0] if len(sv) > 1 else sv[0][0]
            else:
                sv = sv[0]
            pairs = list(zip(self.fraud_features, sv))
            pairs.sort(key=lambda x: abs(x[1]), reverse=True)
            return [{"feature": f, "impact": round(float(i), 4)} for f, i in pairs[:top_n]]
        except Exception:
            # Heuristic fallback
            drivers = []
            if record.get("velocity_1h_count", 0) > 3:
                drivers.append({"feature": "velocity_1h_count", "impact": 0.25})
            if record.get("TransactionAmt", 0) > 50000:
                drivers.append({"feature": "TransactionAmt", "impact": 0.20})
            if record.get("hour_of_day", 12) < 6:
                drivers.append({"feature": "hour_of_day", "impact": 0.15})
            if record.get("geo_mismatch_flag", 0) == 1:
                drivers.append({"feature": "geo_mismatch_flag", "impact": 0.10})
            if record.get("device_change_flag", 0) == 1:
                drivers.append({"feature": "device_change_flag", "impact": 0.08})
            return drivers[:top_n]

    # ------------------------------------------------------------------
    # Fraud probability
    # ------------------------------------------------------------------
    def predict_fraud_prob(self, record: dict) -> float:
        if self.fraud_model is not None:
            X = [_extract_features(record, self.fraud_features)]
            return float(self.fraud_model.predict_proba(X)[0][1])
        # Heuristic fallback
        amt = record.get("TransactionAmt", 0)
        hour = record.get("hour_of_day", 12)
        velocity = record.get("velocity_24h_count", 0)
        score = 0.0
        if amt > 50000:
            score += 0.3
        if hour < 6 or hour > 22:
            score += 0.2
        if velocity > 5:
            score += 0.25
        return min(score, 0.95)

    # ------------------------------------------------------------------
    # False-positive probability
    # ------------------------------------------------------------------
    def predict_fp_prob(self, record: dict) -> float:
        if self.fp_model is not None:
            X = [_extract_features(record, self.fp_features)]
            return float(self.fp_model.predict_proba(X)[0][1])
        # Heuristic fallback
        tenure = record.get("customer_tenure_days", 0)
        refunds = record.get("customer_refund_rate", 0)
        score = 0.0
        if tenure > 365:
            score -= 0.15
        if refunds > 0.1:
            score += 0.3
        return max(score, 0.0)

    # ------------------------------------------------------------------
    # Review time (deterministic heuristic)
    # ------------------------------------------------------------------
    def predict_review_time(self, record: dict) -> float:
        """Return estimated review time in minutes."""
        is_fraud = record.get("is_fraud", 0)
        amount = record.get("TransactionAmt", 0)
        base = 8.0 if is_fraud else 1.0
        return base + (amount / 100000.0) * 2.0

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    def health(self) -> dict:
        return {
            "fraud_model_loaded": self.fraud_model is not None,
            "fp_model_loaded": self.fp_model is not None,
            "fraud_threshold": self.fraud_threshold,
            "fp_threshold": self.fp_threshold,
        }


_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager