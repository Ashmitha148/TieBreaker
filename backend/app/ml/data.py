import csv
import math
import random
import os
from datetime import datetime, timedelta

SEED = int(os.getenv('ML_RANDOM_SEED', '42'))
random.seed(SEED)

CATEGORIES = ['Retail', 'SaaS', 'B2B', 'Services', 'Food', 'Logistics']
BANKS = ['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak', 'Yes', 'PNB', 'Canara']
METHODS = ['upi', 'card', 'netbanking', 'wallet']

# NOTE ON LABEL GENERATION
# --------------------------------------------------------------------------
# Fraud/false-positive labels used to be assigned by a hard coin-flip and
# then the "tell" features (velocity, geo, device, hour) were deterministically
# stamped onto the row to match. That let a model trained on those same
# features achieve ~1.000 precision/recall - it was just reading the label
# back off the features that generated it.
#
# Instead we compute a continuous fraud_score from noisy versions of the
# behavioral features, sample the label from Bernoulli(fraud_score), and then
# deliberately break the correlation for a slice of rows (adversarial fraud
# that looks clean, and noisy legitimate bursts that look risky). This keeps
# the label statistically related to the features without being a
# deterministic function of them, so no single feature can fully explain it.
# --------------------------------------------------------------------------


def sigmoid(x):
    return 1 / (1 + math.exp(-max(-60, min(60, x))))


def generate_dataset(n=8000, n_merchants=200, days=90):
    records = []
    start = datetime(2024, 1, 1)

    merchants = []
    for m in range(n_merchants):
        cat = random.choice(CATEGORIES)
        base = {'Retail': 2500, 'SaaS': 1200, 'B2B': 45000, 'Services': 3500, 'Food': 800, 'Logistics': 15000}[cat]
        merchants.append({
            'merchant_id': f'M{m:04d}',
            'merchant_category': cat,
            'merchant_volume_tier': random.choice(['low', 'mid', 'high']),
            'base_amount': base
        })

    customers = []
    for c in range(1500):
        tenure = random.choices(['new', 'regular', 'vip'], weights=[30, 50, 20])[0]
        if tenure == 'new':
            td, tc, avg = random.randint(5, 25), random.randint(1, 4), random.randint(500, 2000)
        elif tenure == 'regular':
            td, tc, avg = random.randint(60, 300), random.randint(5, 20), random.randint(1000, 8000)
        else:
            td, tc, avg = random.randint(730, 1000), random.randint(50, 120), random.randint(3000, 25000)
        customers.append({
            'customer_id': f'C{c:05d}',
            'customer_tenure_days': td,
            'customer_tx_count_30d': tc,
            'customer_avg_tx_size': avg,
            'customer_refund_rate': round(random.betavariate(2, 20) if tenure != 'vip' else random.betavariate(1, 50), 4),
            'segment': tenure
        })

    tx_id = 0
    cust_history = {c['customer_id']: [] for c in customers}

    fraud_adversarial_count = 0
    legit_false_alarm_count = 0

    for day in range(1, days + 1):
        date = start + timedelta(days=day)
        n_day = max(50, (n // days) + random.randint(-10, 10))

        for _ in range(n_day):
            merchant = random.choice(merchants)
            customer = random.choice(customers)

            base = merchant['base_amount']
            cust_avg = customer['customer_avg_tx_size']
            amount = random.lognormvariate(mu=math.log((base + cust_avg) / 2), sigma=0.6)
            amount = max(200, min(200000, amount))

            hour_weights = [1,1,1,1,1,2,3,5,6,7,7,7,6,6,6,5,5,5,6,6,5,4,3,2]
            hour = random.choices(range(24), weights=hour_weights)[0]
            ts = date + timedelta(hours=hour, minutes=random.randint(0, 59))

            recent_1h = [h for h in cust_history[customer['customer_id']] if h > ts - timedelta(hours=1)]
            recent_24h = [h for h in cust_history[customer['customer_id']] if h > ts - timedelta(hours=24)]
            recent_7d = [h for h in cust_history[customer['customer_id']] if h > ts - timedelta(days=7)]

            v1h = len(recent_1h)
            v24h = len(recent_24h)
            v7d = len(recent_7d)

            # Organic, low base-rate signals - NOT conditioned on fraud yet.
            geo_flag = 1 if random.random() < 0.06 else 0
            device_flag = 1 if random.random() < 0.09 else 0

            # --- Probabilistic fraud scoring ---
            # Gaussian noise on velocity/amount before they ever touch the score,
            # so the score itself is a noisy read of the "true" behavior. Amount
            # is capped at a fixed scale (not the per-transaction max) so it's
            # comparable across merchant categories with very different ticket
            # sizes (a ₹45k B2B invoice isn't inherently riskier than a ₹45k
            # Retail purchase).
            velocity_noisy = max(0.0, v1h + random.gauss(0, 0.12))
            amount_noisy = max(0.0, amount + random.gauss(0, amount * 0.01))

            norm_velocity = min(velocity_noisy, 8) / 8
            norm_amount = min(amount_noisy, 60000) / 60000
            if hour in (1, 2, 3, 4, 5):
                late_hour_risk = 1.0
            elif hour in (0, 22, 23):
                late_hour_risk = 0.4
            else:
                late_hour_risk = 0.0

            base_score = (
                -3.4
                + 8.5 * norm_velocity
                + 6.0 * norm_amount
                + 2.6 * late_hour_risk
                + 4.2 * geo_flag
                + 3.8 * device_flag
            )
            fraud_score = sigmoid(base_score + random.gauss(0, 0.08))
            is_fraud = 1 if random.random() < fraud_score else 0

            # 5% of fraud cases are adversarial: they deliberately do NOT show
            # the velocity/geo/device "tells" - a model that only learns those
            # tells will always miss this slice.
            if is_fraud == 1 and random.random() < 0.05:
                fraud_adversarial_count += 1
                v1h = random.randint(0, 1)
                geo_flag = 0
                device_flag = 0

            # 10% of legitimate transactions get a high-velocity burst (e.g. a
            # customer buying several items back-to-back) - false alarms the
            # model has to learn NOT to key off velocity alone.
            if is_fraud == 0 and random.random() < 0.10:
                legit_false_alarm_count += 1
                v1h = random.randint(6, 14)

            # --- Probabilistic false-positive (bad-flag) scoring ---
            # High amount + low tenure + unusual hour, only possible when the
            # transaction is not actually fraud.
            is_fp = 0
            if is_fraud == 0:
                new_customer = 1.0 if customer['customer_tenure_days'] < 30 else 0.0
                fp_base = (
                    -3.2
                    + 3.0 * norm_amount
                    + 2.6 * new_customer
                    + 2.2 * device_flag
                    + 2.2 * geo_flag
                    + 1.2 * late_hour_risk
                )
                fp_score = sigmoid(fp_base + random.gauss(0, 0.3))
                is_fp = 1 if random.random() < fp_score else 0

            # Heuristic "flagged" field - what a simple threshold rule would
            # have caught, kept for demo/monitoring purposes. Distinct from
            # the true label so it can disagree with it (that disagreement is
            # what the ML model exists to correct).
            is_flagged = 1 if fraud_score > 0.5 or is_fraud == 1 else 0

            records.append({
                'transaction_id': f'TXN{tx_id:07d}',
                'timestamp': ts.isoformat(),
                'day': day,
                'merchant_id': merchant['merchant_id'],
                'merchant_category': merchant['merchant_category'],
                'merchant_volume_tier': merchant['merchant_volume_tier'],
                'customer_id': customer['customer_id'],
                'customer_tenure_days': customer['customer_tenure_days'],
                'customer_tx_count_30d': customer['customer_tx_count_30d'],
                'customer_avg_tx_size': customer['customer_avg_tx_size'],
                'customer_refund_rate': customer['customer_refund_rate'],
                'amount': round(amount, 2),
                'payment_method': random.choice(METHODS),
                'bank_name': random.choice(BANKS),
                'card_bin': str(random.randint(400000, 599999)),
                'hour_of_day': hour,
                'day_of_week': ts.weekday(),
                'is_weekend': 1 if ts.weekday() >= 5 else 0,
                'velocity_1h': v1h,
                'velocity_24h': v24h,
                'velocity_7d': v7d,
                'device_change_flag': device_flag,
                'geo_mismatch_flag': geo_flag,
                'is_cross_border': 1 if random.random() < 0.02 else 0,
                '3ds_used': 1 if random.random() < 0.30 else 0,
                'is_fraud': is_fraud,
                'is_flagged': is_flagged,
                'is_false_positive': is_fp,
                'settlement_time_hours': random.randint(12, 72)
            })

            cust_history[customer['customer_id']].append(ts)
            tx_id += 1

    # Inject counterintuitive demo case
    records.append({
        'transaction_id': 'TXN-COUNTER-001',
        'timestamp': (start + timedelta(days=65, hours=23, minutes=30)).isoformat(),
        'day': 66,
        'merchant_id': 'M0001',
        'merchant_category': 'Retail',
        'merchant_volume_tier': 'high',
        'customer_id': 'C00001',
        'customer_tenure_days': 912,
        'customer_tx_count_30d': 4,
        'customer_avg_tx_size': 3200,
        'customer_refund_rate': 0.0,
        'amount': 48000.0,
        'payment_method': 'card',
        'bank_name': 'HDFC',
        'card_bin': '400000',
        'hour_of_day': 23,
        'day_of_week': 3,
        'is_weekend': 0,
        'velocity_1h': 1,
        'velocity_24h': 2,
        'velocity_7d': 4,
        'device_change_flag': 1,
        'geo_mismatch_flag': 0,
        'is_cross_border': 0,
        '3ds_used': 0,
        'is_fraud': 0,
        'is_flagged': 1,
        'is_false_positive': 1,
        'settlement_time_hours': 24
    })

    print(f'Adversarial (clean-looking) fraud rows: {fraud_adversarial_count}')
    print(f'Legit high-velocity false-alarm rows: {legit_false_alarm_count}')

    return records


def save_csv(records, filename):
    if not records:
        return
    keys = records[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)


def _check_feature_importance_spread(records, max_allowed=0.6, min_features_used=4):
    """Sanity check: train a quick GradientBoostingClassifier on the same
    features used in production (see train_models.FRAUD_FEATURES) and verify
    no single feature dominates. Returns (ok, importances_dict).
    Import is local so `data.py` has no hard dependency on sklearn at import
    time (e.g. for lightweight environments that only generate CSVs).
    """
    from sklearn.ensemble import GradientBoostingClassifier

    feature_names = [
        "amount", "velocity_1h", "velocity_24h", "device_change_flag",
        "geo_mismatch_flag", "is_cross_border", "hour_of_day",
        "customer_tenure_days", "customer_tx_count_30d", "customer_refund_rate"
    ]
    X = [[r[f] for f in feature_names] for r in records]
    y = [r['is_fraud'] for r in records]

    model = GradientBoostingClassifier(random_state=SEED)
    model.fit(X, y)

    importances = dict(zip(feature_names, model.feature_importances_))
    max_importance = max(importances.values())
    used = sum(1 for v in importances.values() if v > 0.01)
    ok = max_importance <= max_allowed and used >= min_features_used
    return ok, importances


if __name__ == '__main__':
    records = generate_dataset()
    train = [r for r in records if r['day'] <= 50]
    val = [r for r in records if 50 < r['day'] <= 70]
    test = [r for r in records if r['day'] > 70]

    os.makedirs('app/ml/data', exist_ok=True)
    save_csv(records, 'app/ml/data/full.csv')
    save_csv(train, 'app/ml/data/train.csv')
    save_csv(val, 'app/ml/data/val.csv')
    save_csv(test, 'app/ml/data/test.csv')

    fraud_count = sum(1 for r in records if r['is_fraud'])
    fp_count = sum(1 for r in records if r['is_false_positive'])
    print(f'Generated: {len(records)} rows. Train: {len(train)}, Val: {len(val)}, Test: {len(test)}')
    print(f'Fraud rate: {fraud_count/len(records):.2%}')
    print(f'FP rate: {fp_count/len(records):.2%}')
    print(f'Generation seed (ML_RANDOM_SEED): {SEED}')

    try:
        ok, importances = _check_feature_importance_spread(records)
        print('Feature importances (GradientBoostingClassifier sanity check):')
        for k, v in sorted(importances.items(), key=lambda kv: -kv[1]):
            print(f'  {k}: {v:.3f}')
        if not ok:
            print('WARNING: feature importance spread check FAILED - increase noise/adversarial rates in data.py')
    except ImportError:
        print('sklearn not installed - skipping feature importance sanity check')