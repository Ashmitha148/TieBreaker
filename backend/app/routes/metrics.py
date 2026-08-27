from fastapi import APIRouter
from pathlib import Path
import pickle

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
ARTIFACTS_DIR = BASE_DIR / 'ml' / 'artifacts'

def _load_or_create_models():
    try:
        with open(ARTIFACTS_DIR / 'fraud_model.pkl', 'rb') as f:
            fraud = pickle.load(f)
        with open(ARTIFACTS_DIR / 'fp_model.pkl', 'rb') as f:
            fp = pickle.load(f)
        return fraud, fp
    except Exception as e:
        # Fallback: recreate models if pickle fails (Railway/Linux compatibility)
        from app.ml.models import FraudModel, FPModel
        from app.ml.train_models import evaluate, load_csv, FEATURES_FRAUD, FEATURES_FP
        DATA_DIR = BASE_DIR / 'ml' / 'data'
        test = load_csv(DATA_DIR / 'test.csv')
        
        from app.ml.train_models import compute_fraud_score, compute_fp_score
        fraud_metrics = evaluate(test, compute_fraud_score, 'is_fraud')
        fp_metrics = evaluate(test, compute_fp_score, 'is_false_positive')
        
        fraud = {'model': FraudModel(), 'features': list(test[0].keys()), 'metrics': fraud_metrics}
        fp = {'model': FPModel(), 'features': list(test[0].keys()), 'metrics': fp_metrics}
        
        # Save for next time
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        pickle.dump(fraud, open(ARTIFACTS_DIR / 'fraud_model.pkl', 'wb'))
        pickle.dump(fp, open(ARTIFACTS_DIR / 'fp_model.pkl', 'wb'))
        return fraud, fp

@router.get('/metrics')
def get_metrics():
    try:
        fraud, fp = _load_or_create_models()
        metrics = {
            'fraud_precision': round(fraud['metrics']['precision'], 3),
            'fraud_recall': round(fraud['metrics']['recall'], 3),
            'fraud_f1': round(fraud['metrics']['f1'], 3),
            'fraud_pr_auc': round(fraud['metrics']['pr_auc'], 3),
            'fp_precision': round(fp['metrics']['precision'], 3),
            'fp_recall': round(fp['metrics']['recall'], 3),
            'fp_pr_auc': round(fp['metrics']['pr_auc'], 3),
            'disclaimer': 'Synthetic data. Production would use actual chargeback fees and LTV data.'
        }
        return metrics
    except Exception as e:
        return {'error': str(e), 'disclaimer': 'Models not available'}
