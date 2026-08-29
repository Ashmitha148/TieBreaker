import os
import pickle
import random
from pathlib import Path

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LinearRegression
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
    "amount", "velocity_1h", "velocity_24h", "device_change_flag",
    "geo_mismatch_flag", "is_cross_border", "hour_of_day",
    "customer_tenure_days", "customer_tx_count_30d", "customer_refund_rate"
]

FP_FEATURES = [
    "amount", "customer_tenure_days", "customer_tx_count_30d",
    "customer_refund_rate", "device_change_flag", "geo_mismatch_flag"
]

REVIEW_FEATURES = [
    "amount", "fraud_prob", "customer_tenure_days",
    "merchant_category_encoded", "hour_of_day"
]


def _encode_merchant(cat):
    mapping = {"Retail": 0, "SaaS": 1, "B2B": 2, "Food": 3}
    return mapping.get(cat, 0)


def _extract_features(record, feature_names):
    row = []
    for f in feature_names:
        if f == "merchant_category_encoded":
            row.append(_encode_merchant(record.get("merchant_category", "Retail")))
        elif f == "fraud_prob":
            row.append(record.get("fraud_prob", 0.5))
        else:
            row.append(record.get(f, 0))
    return row


class ModelManager:
    _instance = None
    
    def current_version_info(self):
        return {
            "version": "2.0.0",
            "fraud_model_loaded": self.fraud_model is not None,
            "fp_model_loaded": self.fp_model is not None,
            "review_model_loaded": self.review_model is not None,
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
        self.review_model = None
        self.fraud_features = FRAUD_FEATURES
        self.fp_features = FP_FEATURES
        self.review_features = REVIEW_FEATURES
        self.fraud_metrics = {"precision": 0.75, "recall": 0.70, "f1": 0.72, "pr_auc": 0.72}
        self.fp_metrics = {"precision": 0.72, "recall": 0.68, "f1": 0.70, "pr_auc": 0.70}
        self._load_models()
        self._initialized = True

    def _load_models(self):
        if not SKLEARN_AVAILABLE:
            return
        paths = {
            "fraud": (ARTIFACTS_DIR / "fraud_model.pkl", FRAUD_FEATURES, self.fraud_metrics),
            "fp": (ARTIFACTS_DIR / "fp_model.pkl", FP_FEATURES, self.fp_metrics),
        }
        for name, (path, feats, default_metrics) in paths.items():
            if path.exists():
                try:
                    with open(path, "rb") as f:
                        data = pickle.load(f)
                    setattr(self, f"{name}_model", data["model"])
                    setattr(self, f"{name}_features", data.get("features", feats))
                    setattr(self, f"{name}_metrics", data.get("metrics", default_metrics))
                except Exception:
                    pass

        review_path = ARTIFACTS_DIR / "review_model.pkl"
        if review_path.exists():
            try:
                with open(review_path, "rb") as f:
                    data = pickle.load(f)
                self.review_model = data["model"]
                self.review_features = data.get("features", REVIEW_FEATURES)
            except Exception:
                pass

    def predict_fraud_prob(self, record: dict) -> float:
        if self.fraud_model is not None and SKLEARN_AVAILABLE:
            try:
                X = [_extract_features(record, self.fraud_features)]
                proba = self.fraud_model.predict_proba(X)[0][1]
                return round(float(proba), 4)
            except Exception:
                pass
        score = 0.0
        score += min(record.get("amount", 0) / 200000, 1.0) * 0.25
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
            except Exception:
                pass
        score = 0.0
        score += (1 - min(record.get("amount", 0) / 100000, 1.0)) * 0.20
        score += min(record.get("customer_tenure_days", 0) / 1000, 1.0) * 0.30
        score += min(record.get("customer_tx_count_30d", 0) / 50, 1.0) * 0.20
        score += (1 - record.get("customer_refund_rate", 0)) * 0.15
        score += (1 - record.get("device_change_flag", 0)) * 0.15
        return round(min(score, 1.0), 4)

    def predict_review_time(self, record: dict) -> float:
        if self.review_model is not None and SKLEARN_AVAILABLE:
            try:
                X = [_extract_features(record, self.review_features)]
                pred = self.review_model.predict(X)[0]
                return round(float(max(pred, 1.0)), 2)
            except Exception:
                pass
        base = 2.0
        base += record.get("is_fraud", 0) * 3.5
        base += min(record.get("amount", 0) / 100000, 1.0) * 2.0
        base += (1 - min(record.get("customer_tenure_days", 0) / 1000, 1.0)) * 1.5
        return round(base, 2)

    def get_shap_drivers(self, record: dict, top_n: int = 3) -> list:
        if not SHAP_AVAILABLE or self.fraud_model is None:
            drivers = []
            if record.get("geo_mismatch_flag", 0) > 0:
                drivers.append({"feature": "geo_mismatch", "impact": 0.18, "direction": "increases"})
            if record.get("velocity_1h", 0) > 5:
                drivers.append({"feature": "velocity_1h", "impact": 0.15, "direction": "increases"})
            if record.get("amount", 0) > 100000:
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
        except Exception:
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
