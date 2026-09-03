"""TieBreaker data loader — V2 (leakage-safe, fragmentation-free).

CRITICAL FIXES from V1:
1. amount_zscore replaced with amount_zscore_temporal (past-only).
2. velocity_7d_trend replaced with velocity_7d_count (past-only, excludes current row).
3. FP label uses TRAIN-ONLY quantile (not full-frame).
4. All features concat'd ONCE — zero fragmentation.
5. leakage_check strengthened: also checks correlation with is_false_positive.
6. Feature lists updated to match new feature names.
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

TRANSACTION_CSV = DATA_DIR / "train_transaction.csv"
IDENTITY_CSV = DATA_DIR / "train_identity.csv"

TX_ID_COL = "TransactionID"
TX_DT_COL = "TransactionDT"
TX_FRAUD_COL = "isFraud"
TX_AMT_COL = "TransactionAmt"
IS_FALSE_POSITIVE_COL = "is_false_positive"

try:
    from .features import (
        velocity_1h_count,
        velocity_24h_count,
        velocity_7d_count,
        velocity_24h_amount_sum,
        velocity_24h_amount_mean,
        card1_total_count,
        addr1_total_count,
        merchant_chargeback_rate,
        payment_method_risk_score,
        hours_since_last_txn,
        hour_bin_risk,
        amount_zscore_temporal,
        weekend_flag,
        email_domain_risk,
        device_type_encoded,
        browser_risk,
        screen_size_risk,
        transaction_count_by_card1_hour,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from features import (
        velocity_1h_count,
        velocity_24h_count,
        velocity_7d_count,
        velocity_24h_amount_sum,
        velocity_24h_amount_mean,
        card1_total_count,
        addr1_total_count,
        merchant_chargeback_rate,
        payment_method_risk_score,
        hours_since_last_txn,
        hour_bin_risk,
        amount_zscore_temporal,
        weekend_flag,
        email_domain_risk,
        device_type_encoded,
        browser_risk,
        screen_size_risk,
        transaction_count_by_card1_hour,
    )
# ---------------------------------------------------------------------------
# Feature lists — updated for V2 features
# ---------------------------------------------------------------------------
FRAUD_FEATURES = [
    # Raw IEEE-CIS (high-signal subset)
    "TransactionAmt",
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
    "C11", "C12", "C13", "C14",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
    "D11", "D12", "D13", "D14", "D15",
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10",
    "V11", "V12", "V13", "V14", "V15",
    "card1", "card2", "card3", "card5",
    "card4_encoded", "card6_encoded",
    "addr1", "addr2",
    "hour_of_day",
    "day_of_week",
    "device_change_flag",
    "geo_mismatch_flag",
    "is_cross_border",
    # Engineered temporal (leakage-safe, past-only)
    "velocity_1h_count",
    "velocity_24h_count",
    "velocity_7d_count",
    "velocity_24h_amount_sum",
    "velocity_24h_amount_mean",
    "card1_total_count",
    "addr1_total_count",
    "merchant_chargeback_rate",
    "payment_method_risk_score",
    "hours_since_last_txn",
    "hour_bin_risk",
    "amount_zscore_temporal",
    "weekend_flag",
    "email_domain_risk",
    "device_type_encoded",
    "browser_risk",
    "screen_size_risk",
    "transaction_count_by_card1_hour",
]

FP_FEATURES = [
    "TransactionAmt",
    "C1", "C2", "C3", "C4", "C5",
    "D1", "D2", "D3",
    "V1", "V2", "V3", "V4", "V5",
    "card1", "card2", "card3", "card5",
    "card4_encoded", "card6_encoded",
    "addr1", "addr2",
    "hour_of_day",
    "device_change_flag",
    "geo_mismatch_flag",
    "is_cross_border",
    "velocity_1h_count",
    "velocity_24h_count",
    "velocity_24h_amount_sum",
    "payment_method_risk_score",
    "hours_since_last_txn",
    "hour_bin_risk",
    "amount_zscore_temporal",
    "weekend_flag",
    "email_domain_risk",
    "device_type_encoded",
    "browser_risk",
    "screen_size_risk",
]


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive features. All temporal aggregations are leakage-safe (past-only)."""
    df = df.copy()

    # Temporal features from TransactionDT
    if TX_DT_COL in df.columns:
        df["hour_of_day"] = (df[TX_DT_COL] // 3600) % 24
        df["day_of_week"] = ((df[TX_DT_COL] // 86400) % 7).astype(int)
    else:
        df["hour_of_day"] = 12
        df["day_of_week"] = 0

    # Device change flag
    if "DeviceType" in df.columns:
        df["device_change_flag"] = (
            df["DeviceType"].isna() | (df["DeviceType"] == "")
        ).astype(int)
    elif "id_30" in df.columns:
        df["device_change_flag"] = df["id_30"].isna().astype(int)
    else:
        df["device_change_flag"] = 0

    # Geo mismatch
    if "addr1" in df.columns and "addr2" in df.columns:
        df["geo_mismatch_flag"] = (
            df["addr1"].isna() | df["addr2"].isna()
        ).astype(int)
    else:
        df["geo_mismatch_flag"] = 0

    # Cross-border proxy
    if "addr2" in df.columns:
        df["is_cross_border"] = df["addr2"].isna().astype(int)
    else:
        df["is_cross_border"] = 0

    # Encode categorical card columns
    if "card4" in df.columns:
        card4_map = {"visa": 1, "mastercard": 2, "amex": 3, "discover": 4}
        df["card4_encoded"] = df["card4"].str.lower().map(card4_map).fillna(0).astype(int)
    else:
        df["card4_encoded"] = 0

    if "card6" in df.columns:
        card6_map = {"credit": 1, "debit": 2}
        df["card6_encoded"] = df["card6"].str.lower().map(card6_map).fillna(0).astype(int)
    else:
        df["card6_encoded"] = 0

    # Fill NaNs for numeric columns
    numeric_cols = [c for c in df.columns if df[c].dtype.kind in "iufc"]
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # ------------------------------------------------------------------
    # FP label — rule-based scoring (no quantile yet; that comes post-split)
    # ------------------------------------------------------------------
    if TX_FRAUD_COL in df.columns:
        amt_median = df[TX_AMT_COL].median() if TX_AMT_COL in df.columns else 100.0
        high_amount = (
            (df[TX_AMT_COL] > amt_median * 2.5).astype(int)
            if TX_AMT_COL in df.columns
            else pd.Series(0, index=df.index)
        )
        unusual_hour = (
            ((df["hour_of_day"] >= 0) & (df["hour_of_day"] <= 5))
            .astype(int)
        )
        d1_series = df.get("D1", pd.Series([999] * len(df), index=df.index))
        new_customer = (d1_series < 30).astype(int)
        fp_score = (
            high_amount * 0.25
            + unusual_hour * 0.25
            + new_customer * 0.20
            + df["device_change_flag"] * 0.15
            + df["geo_mismatch_flag"] * 0.15
        )
        df["is_false_positive"] = (
            (df[TX_FRAUD_COL] == 0) & (fp_score > 0.55)
        ).astype(int)
    else:
        df["is_false_positive"] = 0

    # ------------------------------------------------------------------
    # Engineered features — ALL computed as Series, then concat ONCE.
    # This eliminates the fragmentation warning completely.
    # ------------------------------------------------------------------
    engineered = {
        "velocity_1h_count": velocity_1h_count(df),
        "velocity_24h_count": velocity_24h_count(df),
        "velocity_7d_count": velocity_7d_count(df),
        "velocity_24h_amount_sum": velocity_24h_amount_sum(df),
        "velocity_24h_amount_mean": velocity_24h_amount_mean(df),
        "card1_total_count": card1_total_count(df),
        "addr1_total_count": addr1_total_count(df),
        "merchant_chargeback_rate": merchant_chargeback_rate(df),
        "payment_method_risk_score": payment_method_risk_score(df),
        "hours_since_last_txn": hours_since_last_txn(df),
        "hour_bin_risk": hour_bin_risk(df),
        "amount_zscore_temporal": amount_zscore_temporal(df),
        "weekend_flag": weekend_flag(df),
        "email_domain_risk": email_domain_risk(df),
        "device_type_encoded": device_type_encoded(df),
        "browser_risk": browser_risk(df),
        "screen_size_risk": screen_size_risk(df),
        "transaction_count_by_card1_hour": transaction_count_by_card1_hour(df),
    }
    df = pd.concat([df, pd.DataFrame(engineered, index=df.index)], axis=1)

    return df


def leakage_check(df: pd.DataFrame) -> None:
    """Raise ValueError if any feature has >0.90 correlation with target.

    Threshold lowered from 0.95 to 0.90 for stricter leakage detection.
    Also checks is_false_positive correlation.
    """
    numeric_df = df.select_dtypes(include=[np.number])

    for target_col in [TX_FRAUD_COL, IS_FALSE_POSITIVE_COL]:
        if target_col not in numeric_df.columns:
            continue
        corr = numeric_df.corr()[target_col].abs().sort_values(ascending=False)
        suspicious = (
            corr[corr > 0.90]
            .drop(TX_FRAUD_COL, errors="ignore")
            .drop(IS_FALSE_POSITIVE_COL, errors="ignore")
        )
        if not suspicious.empty:
            raise ValueError(
                f"Data leakage detected for {target_col}: features {suspicious.index.tolist()} "
                f"have >0.90 correlation"
            )


def load_data(max_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load IEEE-CIS, engineer features, strict temporal 70/15/15 split."""

    if not TRANSACTION_CSV.exists():
        raise FileNotFoundError(
            f"Real IEEE-CIS transaction data not found at {TRANSACTION_CSV}. "
            f"Place train_transaction.csv and train_identity.csv in {DATA_DIR}."
        )

    tx = pd.read_csv(TRANSACTION_CSV, nrows=max_rows)

    if IDENTITY_CSV.exists():
        idf = pd.read_csv(IDENTITY_CSV)
        df = tx.merge(idf, on=TX_ID_COL, how="left")
    else:
        warnings.warn(
            f"Identity file not found at {IDENTITY_CSV}; proceeding with transaction data only."
        )
        df = tx.copy()

    if TX_FRAUD_COL not in df.columns:
        raise ValueError(f"Required column '{TX_FRAUD_COL}' not found.")

    # Temporal sort — critical to prevent leakage
    if TX_DT_COL in df.columns:
        df = df.sort_values(TX_DT_COL).reset_index(drop=True)
    else:
        warnings.warn(f"Column '{TX_DT_COL}' not found; split may not be temporal.")

    df = _engineer_features(df)

    # ------------------------------------------------------------------
    # FP label — second pass with TRAIN-ONLY quantile (leakage-safe).
    # The quantile is computed on the train split AFTER the temporal split,
    # then applied to all splits. This is the correct way.
    # ------------------------------------------------------------------
    if TX_FRAUD_COL in df.columns and TX_AMT_COL in df.columns:
        # Strict temporal split first
        n = len(df)
        train_end = int(n * 0.70)
        val_end = int(n * 0.85)

        train_df = df.iloc[:train_end]

        # Compute threshold on TRAIN ONLY
        _amt_threshold = train_df[TX_AMT_COL].quantile(0.75)

        # Apply to full frame (train-only threshold is leakage-safe for test)
        df[IS_FALSE_POSITIVE_COL] = (
            (df[TX_FRAUD_COL] == 0)
            & (df[TX_AMT_COL] >= _amt_threshold)
            & (df["is_false_positive"] == 1)  # from rule-based above
        ).astype(int)
    else:
        df[IS_FALSE_POSITIVE_COL] = 0

    leakage_check(df)

    # Strict temporal split: 70 / 15 / 15
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    return train, val, test


def get_feature_matrix(df: pd.DataFrame, feature_names: list) -> np.ndarray:
    """Extract dense NumPy feature matrix. Missing columns filled with 0."""
    available = [f for f in feature_names if f in df.columns]
    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        warnings.warn(f"Missing feature columns (filled with 0): {missing}")
    X = df[available].to_numpy(dtype=np.float64)
    if missing:
        X = np.hstack([X, np.zeros((len(df), len(missing)), dtype=np.float64)])
    return X
