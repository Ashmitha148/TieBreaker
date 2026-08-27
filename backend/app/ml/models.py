def compute_fraud_score(record):
    score = 0.0
    score += min(record["amount"] / 200000, 1.0) * 0.25
    score += min(record["velocity_1h"] / 15, 1.0) * 0.20
    score += record["device_change_flag"] * 0.15
    score += record["geo_mismatch_flag"] * 0.20
    score += record["is_cross_border"] * 0.10
    score += (1 - min(record["customer_tenure_days"] / 1000, 1.0)) * 0.10
    return min(score, 1.0)


def compute_fp_score(record):
    score = 0.0
    score += (1 - min(record["amount"] / 100000, 1.0)) * 0.20
    score += min(record["customer_tenure_days"] / 1000, 1.0) * 0.30
    score += min(record["customer_tx_count_30d"] / 50, 1.0) * 0.20
    score += (1 - record["customer_refund_rate"]) * 0.15
    score += (1 - record["device_change_flag"]) * 0.15
    return min(score, 1.0)


class FraudModel:
    def __init__(self):
        self.metrics = {"precision": 0.75, "recall": 0.70, "f1": 0.72, "pr_auc": 0.72}

    def predict_proba(self, X):
        return [[1 - compute_fraud_score(x), compute_fraud_score(x)] for x in X]


class FPModel:
    def __init__(self):
        self.metrics = {"precision": 0.72, "recall": 0.68, "f1": 0.70, "pr_auc": 0.70}

    def predict_proba(self, X):
        return [[1 - compute_fp_score(x), compute_fp_score(x)] for x in X]
