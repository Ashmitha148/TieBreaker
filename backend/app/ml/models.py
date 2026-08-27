class FraudModel:
    def predict_proba(self, X):
        from app.ml.train_models import compute_fraud_score
        return [[1 - compute_fraud_score(x), compute_fraud_score(x)] for x in X]

class FPModel:
    def predict_proba(self, X):
        from app.ml.train_models import compute_fp_score
        return [[1 - compute_fp_score(x), compute_fp_score(x)] for x in X]
