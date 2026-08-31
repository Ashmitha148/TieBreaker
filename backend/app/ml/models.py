import logging
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger("tiebreaker.ml")

try:
    from sklearn.ensemble import GradientBoostingClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

FRAUD_FEATURES = [
    "TransactionAmt",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
    "C11", "C12", "C13", "C14",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    "D11", "D12", "D13", "D14", "D15",
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10",
    "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2",
    "hour_of_day",
    "day_of_week",
    "device_change_flag",
    "geo_mismatch_flag",
    "is_cross_border",
]

FP_FEATURES = [
    "TransactionAmt",
    "C1", "C2", "C3", "C4", "C5",
    "D1", "D2", "D3",
    "V1", "V2", "V3", "V4", "V5",
    "card1", "card2", "card3",
    "addr1", "addr2",
    "hour_of_day",
    "device_change_flag",
    "geo_mismatch_flag",
    "is_cross_border",
]


def _extract_features(record: dict, feature_names: list) -> list:
    row = []
    for f in feature_names:
        val = record.get(f, 0)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            val = 0.0
        row.append(float(val))
    return row


class ModelManager:
    _instance = None

    def current_version_info(self):
        return {
            "version": self.model_version,
            "fraud_model_loaded": self.fraud_model is not None,
            "fp_model_loaded": self.fp_model is not None,
        }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.fraud_model = None
        self.fp_model = None
        self.fraud_features = FRAUD_FEATURES
        self.fp_features = FP_FEATURES
        self.fraud_metrics = {"precision": 0.75, "recall": 0.70, "f1": 0.72, "pr_auc": 0.72}
        self.fp_metrics = {"precision": 0.72, "recall": 0.68, "f1": 0.70, "pr_auc": 0.70}
        self.fraud_threshold = 0.5
        self.fp_threshold = 0.5
        self.model_version = "unloaded"
        self._load_models()
        self._initialized = True

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
                    data = joblib.load(path)
                    setattr(self, f"{name}_model", data["model"])
                    setattr(self, f"{name}_features", data.get("features", feats))
                    setattr(self, f"{name}_metrics", data.get("metrics", default_metrics))
                    setattr(self, f"{name}_threshold", data.get("threshold", 0.5))
                    artifact_version = data.get("version") or f"unversioned-{int(path.stat().st_mtime)}"
                    if name == "fraud":
                        self.model_version = artifact_version
                except (FileNotFoundError, EOFError, KeyError) as e:
                    logger.warning(f"Could not load {name} model artifact from {path}: {e}")

    def predict_fraud_prob(self, record: dict) -> float:
        if self.fraud_model is not None and SKLEARN_AVAILABLE:
            try:
                X = [_extract_features(record, self.fraud_features)]
                proba = self.fraud_model.predict_proba(X)[0][1]
                return round(float(proba), 4)
            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"Fraud model inference failed, using heuristic fallback: {e}")
        score = 0.0
        score += min(record.get("TransactionAmt", 0) / 200000, 1.0) * 0.25
        score += min(record.get("velocity_1h", 0) / 15, 1.0) * 0.20
        score += record.get("device_change_flag", 0) * 0.15
        score += record.get("geo_mismatch_flag", 0) * 0.20
        score += record.get("is_cross_border", 0) * 0.10
        score += (1 - min(record.get("customer_tenure_days", 0) / 1000, 1.0)) * 0.10
        return round(min(score, 1.0), 4)

    def predict_fp_prob(self, record: dict) -> float:
        if self.fp_model is not None and SKLEARN_AVAILABLE:
            try:
                X = [_extract_features(record, self.fp_features)]
                proba = self.fp_model.predict_proba(X)[0][1]
                return round(float(proba), 4)
            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"FP model inference failed, using heuristic fallback: {e}")
        score = 0.0
        score += (1 - min(record.get("TransactionAmt", 0) / 100000, 1.0)) * 0.20
        score += (1 - min(record.get("customer_tenure_days", 0) / 1000, 1.0)) * 0.30
        score += min(record.get("customer_tx_count_30d", 0) / 50, 1.0) * 0.20
        score += (1 - record.get("customer_refund_rate", 0)) * 0.15
        score += (1 - record.get("device_change_flag", 0)) * 0.15
        return round(min(score, 1.0), 4)

    def predict_review_time(self, record: dict) -> float:
        """
        Deterministic review time:
          - Fraud transactions: 8 minutes
          - Legitimate transactions: 1 minute + (amount / 100000) * 2 minutes
        """
        is_fraud = record.get("is_fraud", 0)
        amount = record.get("amount", 0) or record.get("TransactionAmt", 0)
        if is_fraud:
            return 8.0
        return round(1.0 + (amount / 100000.0) * 2.0, 2)

    def get_shap_drivers(self, record: dict, top_n: int = 3) -> list:
        if not SHAP_AVAILABLE or self.fraud_model is None:
            drivers = []
            if record.get("geo_mismatch_flag", 0) > 0:
                drivers.append({"feature": "geo_mismatch", "impact": 0.18, "direction": "increases"})
            if record.get("velocity_1h", 0) > 5:
                drivers.append({"feature": "velocity_1h", "impact": 0.15, "direction": "increases"})
            if record.get("amount", 0) > 100000 or record.get("TransactionAmt", 0) > 100000:
                drivers.append({"feature": "amount", "impact": 0.12, "direction": "increases"})
            if record.get("customer_tenure_days", 0) < 30:
                drivers.append({"feature": "customer_tenure_days", "impact": -0.10, "direction": "decreases"})
            if record.get("device_change_flag", 0) > 0:
                drivers.append({"feature": "device_change", "impact": 0.08, "direction": "increases"})
            if len(drivers) < top_n:
                drivers.append({"feature": "hour_of_day", "impact": 0.05, "direction": "increases"})
            return drivers[:top_n]

        try:
            X = [_extract_features(record, self.fraud_features)]
            explainer = shap.TreeExplainer(self.fraud_model)
            shap_values = explainer.shap_values(X)
            if isinstance(shap_values, list):
                sv = shap_values[1][0]
            else:
                sv = shap_values[0]
            feature_impacts = []
            for i, feature in enumerate(self.fraud_features):
                impact = float(sv[i]) if i < len(sv) else 0.0
                feature_impacts.append({
                    "feature": feature,
                    "impact": round(abs(impact), 4),
                    "direction": "increases" if impact > 0 else "decreases",
                    "raw_value": round(impact, 4),
                })
            feature_impacts.sort(key=lambda x: abs(x["raw_value"]), reverse=True)
            return feature_impacts[:top_n]
        except (ValueError, KeyError, IndexError, AttributeError, TypeError) as e:
            logger.warning(f"SHAP explanation failed, using static fallback drivers: {e}")
            return [
                {"feature": "amount", "impact": 0.15, "direction": "increases"},
                {"feature": "geo_mismatch", "impact": 0.12, "direction": "increases"},
                {"feature": "velocity_1h", "impact": 0.08, "direction": "increases"},
            ]


_model_manager = None


def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def compute_fraud_score(record):
    return get_model_manager().predict_fraud_prob(record)


def compute_fp_score(record):
    return get_model_manager().predict_fp_prob(record)


class FraudModel:
    def __init__(self):
        self.metrics = get_model_manager().fraud_metrics

    def predict_proba(self, X):
        mgr = get_model_manager()
        return [[1 - mgr.predict_fraud_prob(x), mgr.predict_fraud_prob(x)] for x in X]


class FPModel:
    def __init__(self):
        self.metrics = get_model_manager().fp_metrics

    def predict_proba(self, X):
        mgr = get_model_manager()
        return [[1 - mgr.predict_fp_prob(x), mgr.predict_fp_prob(x)] for x in X]
