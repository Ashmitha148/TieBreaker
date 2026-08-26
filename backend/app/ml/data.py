import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_synthetic_data():
    # Deterministic seed
    seed = int(os.getenv('ML_RANDOM_SEED', '42'))
    np.random.seed(seed)
    # Generate merchants
    categories = ['Retail', 'SaaS', 'B2B', 'Services', 'Food', 'Logistics']
    merchants = []
    merchant_id = 1
    for i, cat in enumerate(categories):
        count = 33 + (1 if i < 2 else 0)  # first two categories get extra merchant
        for _ in range(count):
            merchants.append({'merchant_id': merchant_id, 'category': cat, 'name': f'Merchant_{merchant_id}'})
            merchant_id += 1
    merchant_df = pd.DataFrame(merchants)

    # Daily transaction counts
    days = 90
    base_tx_per_day = 88
    extra_days = 80  # first 80 days get one extra transaction
    rows = []
    tx_id = 1
    start_date = datetime.utcnow().date() - timedelta(days=days)
    for day in range(1, days + 1):
        date = start_date + timedelta(days=day)
        tx_count = base_tx_per_day + (1 if day <= extra_days else 0)
        for _ in range(tx_count):
            # Customer mix
            r = np.random.rand()
            if r < 0.30:
                customer_type = 'New'
            elif r < 0.80:
                customer_type = 'Regular'
            else:
                customer_type = 'VIP'
            # Payment method
            r = np.random.rand()
            if r < 0.40:
                method = 'UPI'
            elif r < 0.75:
                method = 'Card'
            elif r < 0.90:
                method = 'Netbanking'
            else:
                method = 'Wallet'
            # Bank
            banks = ['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak', 'Yes', 'PNB', 'Canara']
            bank = np.random.choice(banks)
            # Amount
            amount = np.random.lognormal(mean=5, sigma=1)
            amount = int(min(max(amount, 200), 200000))
            # Merchant assignment
            merchant = merchant_df.sample(1).iloc[0]
            # Fraud label
            is_fraud = (tx_id % 20 == 0)
            # Flag rule
            is_flagged = amount > 150000
            rows.append({
                'transaction_id': tx_id,
                'timestamp': datetime.combine(date, datetime.min.time()),
                'merchant_id': merchant['merchant_id'],
                'merchant_category': merchant['category'],
                'customer_type': customer_type,
                'payment_method': method,
                'bank_name': bank,
                'amount': amount,
                'is_fraud': is_fraud,
                'is_flagged': is_flagged,
                'source': 'synthetic'
            })
            tx_id += 1
    df = pd.DataFrame(rows)
    # Derived features (simplified deterministic placeholders)
    df['velocity_24h'] = 0
    df['customer_tx_count_30d'] = 0
    df['3ds_used'] = (np.random.rand(len(df)) < 0.20).astype(int)
    return df
