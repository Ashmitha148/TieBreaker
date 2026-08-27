from fastapi import APIRouter
import pickle
from pathlib import Path

router = APIRouter()

@router.get('/metrics')
def get_metrics():
    artifacts = Path(__file__).parent.parent / 'ml' / 'artifacts'
    metrics = {}
    try:
        with open(artifacts / 'fraud_model.pkl', 'rb') as f:
            fraud = pickle.load(f)
            metrics['fraud_precision'] = round(fraud['metrics']['precision'], 3)
            metrics['fraud_recall'] = round(fraud['metrics']['recall'], 3)
            metrics['fraud_f1'] = round(fraud['metrics']['f1'], 3)
            metrics['fraud_pr_auc'] = round(fraud['metrics']['pr_auc'], 3)
    except Exception as e:
        metrics['fraud_error'] = str(e)
    
    try:
        with open(artifacts / 'fp_model.pkl', 'rb') as f:
            fp = pickle.load(f)
            metrics['fp_precision'] = round(fp['metrics']['precision'], 3)
            metrics['fp_recall'] = round(fp['metrics']['recall'], 3)
            metrics['fp_pr_auc'] = round(fp['metrics']['pr_auc'], 3)
    except Exception as e:
        metrics['fp_error'] = str(e)
    
    metrics['disclaimer'] = 'Synthetic data. Production would use actual chargeback fees and LTV data.'
    return metrics
