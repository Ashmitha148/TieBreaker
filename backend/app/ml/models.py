import hashlib
import logging
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

# Feature lists (defined here to avoid circular import with predictor.py)
FRAUD_FEATURES = [
    "TransactionAmt", "card1", "card2", "card3", "card5",
    "addr1", "addr2", "dist1", "dist2",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
    "C11", "C12", "C13", "C14",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    "D11", "D12", "D13", "D14", "D15",
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10",
    "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20",
    "V21", "V22", "V23", "V24", "V25", "V26", "V27", "V28", "V29", "V30",
    "V31", "V32", "V33", "V34", "V35", "V36", "V37", "V38", "V39", "V40",
    "V41", "V42", "V43", "V44", "V45", "V46", "V47", "V48", "V49", "V50",
    "V51", "V52", "V53", "V54", "V55", "V56", "V57", "V58", "V59", "V60",
    "V61", "V62", "V63", "V64", "V65", "V66", "V67", "V68", "V69", "V70",
    "V71", "V72", "V73", "V74", "V75", "V76", "V77", "V78", "V79", "V80",
    "V81", "V82", "V83", "V84", "V85", "V86", "V87", "V88", "V89", "V90",
    "V91", "V92", "V93", "V94", "V95", "V96", "V97", "V98", "V99", "V100",
    "hour_of_day", "day_of_week", "device_change_flag", "geo_mismatch_flag",
    "is_cross_border", "customer_tenure_days", "customer_tx_count_30d",
    "customer_refund_rate", "velocity_1h", "velocity_24h",
]

FP_FEATURES = [
    "TransactionAmt", "card1", "card2", "card3", "card5",
    "addr1", "addr2",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
    "C11", "C12", "C13", "C14",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    "D11", "D12", "D13", "D14", "D15",
    "hour_of_day", "day_of_week", "device_change_flag",
    "customer_tenure_days", "customer_tx_count_30d", "customer_refund_rate",
    "velocity_1h", "velocity_24h",
]

try:
    from sklearn.ensemble import GradientBoostingClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


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
        if not SKLEARN_AVAILABLE:
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
                    logger.info(f"Loaded {name} model from {path}")
                except Exception as e:
                    logger.warning(f"Failed to load {name} model: {e}")
            else:
                logger.warning(f"{name} model artifact not found at {path}")

    # ------------------------------------------------------------------
    # Version info
    # ------------------------------------------------------------------
    def current_version_info(self) -> dict:
        return {
            "version": "gbc-fraud-v2",
            "fraud_threshold": self.fraud_threshold,
            "fp_threshold": self.fp_threshold,
        }

    def get_shap_drivers(self, record: dict, top_n: int = 3) -> list:
        try:
            import shap
            if self.fraud_model is None:
                raise RuntimeError("Fraud model not loaded")
            explainer = shap.TreeExplainer(self.fraud_model)
            features = _extract_features(record, self.fraud_features)
            sv = explainer.shap_values([features])
            if isinstance(sv, list):
                sv = sv[1][0]
            pairs = list(zip(self.fraud_features, sv))
            pairs.sort(key=lambda x: abs(x[1]), reverse=True)
            return [{"feature": f, "impact": round(float(i), 4)} for f, i in pairs[:top_n]]
        except Exception:
            # Heuristic fallback — NEVER crash the API for explainability
            drivers = []
            if record.get("velocity_1h", 0) > 3:
                drivers.append({"feature": "velocity_1h", "impact": 0.25})
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
        velocity = record.get("velocity_24h", 0)
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
    # Review time (deterministic heuristic — no ML model)
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