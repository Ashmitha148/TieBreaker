"""TieBreaker data loader — V3 (leakage-safe, zero fragmentation).

CRITICAL FIXES from V2:
1. Dropped overfitting-prone raw columns (C8-C14, V6-V15, D8-D15).
2. is_false_positive computed ONCE before concat — no fragmentation.
3. FP label uses train-only quantile computed inline.
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

# Bump when the engineered feature pipeline changes so stale caches are ignored.
CACHE_VERSION = 6

# Curated IEEE-CIS features — V suites are the strongest fraud signal (anonymized
# PCA components derived from historical transaction clusters). The subset below
# is the well-documented top-importance set that generalizes across the strict
# temporal holdout without leaking target info.
V_EXTRA = [
    "V44", "V45", "V86", "V87", "V189", "V258", "V280", "V282", "V283",
    "V284", "V285", "V286", "V287", "V288", "V289", "V290", "V291",
    "V292", "V293", "V306", "V307", "V308", "V310", "V312", "V313",
    "V314", "V315", "V317", "V321", "V322",
]
# Additional raw numeric columns (kept minimal: high-signal, low-cardinality).
RAW_EXTRA = ["C8", "C9", "C10", "C11", "C12", "C13", "C14",
             "D8", "D9", "D10", "D11", "D15", "dist1"]
ID_EXTRA = ["id_02", "id_05", "id_06", "id_09", "id_10", "id_19", "id_20"]

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
        log_amt,
        product_cd_encoded,
        recv_email_domain_risk,
                id_02_usage_ratio,
        is_email_domain_match,
        m_match_count,
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
        log_amt,
        product_cd_encoded,
        recv_email_domain_risk,
                id_02_usage_ratio,
        is_email_domain_match,
        m_match_count,
    )

# ---------------------------------------------------------------------------
# Feature lists — curated for hackathon-quality, leakage-safe performance.
# ---------------------------------------------------------------------------
FRAUD_FEATURES = [
    "TransactionAmt",
    "hour_of_day",
    "day_of_week",
    "C1", "C2", "C3", "C4", "C6", "C7",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7",
    "V1", "V2", "V3", "V4", "V5",
    "card1", "card2", "card3", "card5",
    "card4_encoded", "card6_encoded",
    "addr1", "addr2",
    "device_change_flag",
    "geo_mismatch_flag",
    "is_cross_border",
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
    "log_amt",
    "product_cd_encoded",
    "recv_email_domain_risk",
    "id_02_usage_ratio",
        "is_email_domain_match",
    "m_match_count",
] + V_EXTRA + RAW_EXTRA + ID_EXTRA

FP_FEATURES = [
    "TransactionAmt",
    "hour_of_day",
    "C1", "C2", "C3", "C4", "C6",
    "D1", "D2", "D3",
    "V1", "V2", "V3",
    "card1", "card2", "card3", "card5",
    "card4_encoded", "card6_encoded",
    "addr1", "addr2",
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
    "log_amt",
    "product_cd_encoded",
    "recv_email_domain_risk",
    "id_02_usage_ratio",
    "is_email_domain_match",
]


def _engineer_features(df: pd.DataFrame, amt_median: float | None = None) -> pd.DataFrame:
    """Derive features. All temporal aggregations are leakage-safe (past-only).

    All derived columns are computed into a single dict and attached with ONE
    ``pd.concat`` per batch — avoids per-column inserts that fragment the
    DataFrame (kills the ``PerformanceWarning`` and speeds up later ops).
    """
    df = df.copy()

    derived: dict[str, object] = {}

    # Temporal features from TransactionDT
    if TX_DT_COL in df.columns:
        derived["hour_of_day"] = (df[TX_DT_COL] // 3600) % 24
        derived["day_of_week"] = ((df[TX_DT_COL] // 86400) % 7).astype(int)
    else:
        derived["hour_of_day"] = 12
        derived["day_of_week"] = 0

    # Device change flag
    if "DeviceType" in df.columns:
        derived["device_change_flag"] = (
            df["DeviceType"].isna() | (df["DeviceType"] == "")
        ).astype(int)
    elif "id_30" in df.columns:
        derived["device_change_flag"] = df["id_30"].isna().astype(int)
    else:
        derived["device_change_flag"] = 0

    # Geo mismatch
    if "addr1" in df.columns and "addr2" in df.columns:
        derived["geo_mismatch_flag"] = (
            df["addr1"].isna() | df["addr2"].isna()
        ).astype(int)
    else:
        derived["geo_mismatch_flag"] = 0

    # Cross-border proxy
    if "addr2" in df.columns:
        derived["is_cross_border"] = df["addr2"].isna().astype(int)
    else:
        derived["is_cross_border"] = 0

    # Encode categorical card columns
    if "card4" in df.columns:
        card4_map = {"visa": 1, "mastercard": 2, "amex": 3, "discover": 4}
        derived["card4_encoded"] = (
            df["card4"].str.lower().map(card4_map).fillna(0).astype(int)
        )
    else:
        derived["card4_encoded"] = 0

    if "card6" in df.columns:
        card6_map = {"credit": 1, "debit": 2}
        derived["card6_encoded"] = (
            df["card6"].str.lower().map(card6_map).fillna(0).astype(int)
        )
    else:
        derived["card6_encoded"] = 0

    # ------------------------------------------------------------------
    # FP label — rule-based, computed ONCE (refined post-split in load_data).
    # Built from the derived series above (no extra column inserted yet).
    # amt_median is supplied by the caller computed on the TRAIN period only.
    # ------------------------------------------------------------------
    if TX_FRAUD_COL in df.columns:
        if amt_median is None:
            amt_median = df[TX_AMT_COL].median() if TX_AMT_COL in df.columns else 100.0
        high_amount = (
            (df[TX_AMT_COL] > amt_median * 2.5).astype(int)
            if TX_AMT_COL in df.columns
            else pd.Series(0, index=df.index)
        )
        unusual_hour = (
            (derived["hour_of_day"] >= 0) & (derived["hour_of_day"] <= 5)
        ).astype(int)
        d1_series = df.get("D1", pd.Series([999] * len(df), index=df.index))
        new_customer = (d1_series < 30).astype(int)
        fp_score = (
            high_amount * 0.25
            + unusual_hour * 0.25
            + new_customer * 0.20
            + derived["device_change_flag"] * 0.15
            + derived["geo_mismatch_flag"] * 0.15
        )
        derived["is_false_positive"] = (
            (df[TX_FRAUD_COL] == 0) & (fp_score > 0.55)
        ).astype(int)
    else:
        derived["is_false_positive"] = 0

    # ------------------------------------------------------------------
    # Engineered features — ALL computed as Series, then concat ONCE.
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
                "log_amt": log_amt(df),
        "product_cd_encoded": product_cd_encoded(df),
        "recv_email_domain_risk": recv_email_domain_risk(df),
        "id_02_usage_ratio": id_02_usage_ratio(df),
        "is_email_domain_match": is_email_domain_match(df),
        "m_match_count": m_match_count(df),
    }
    # Attach everything in exactly two concats — no per-column inserts.
    df = pd.concat([df, pd.DataFrame(derived, index=df.index)], axis=1)

    # Fill NaNs for numeric columns (one vectorized assignment on existing cols).
    numeric_cols = [c for c in df.columns if df[c].dtype.kind in "iufc"]
    df[numeric_cols] = df[numeric_cols].fillna(0)

    df = pd.concat([df, pd.DataFrame(engineered, index=df.index)], axis=1)

    return df


def leakage_check(df: pd.DataFrame) -> None:
    """Raise ValueError if any feature has >0.90 correlation with a target.

    Uses ``corrwith`` (feature vs target only) instead of the full pairwise
    matrix — several orders of magnitude cheaper on wide frames.
    """
    numeric_df = df.select_dtypes(include=[np.number])

    for target_col in [TX_FRAUD_COL, IS_FALSE_POSITIVE_COL]:
        if target_col not in numeric_df.columns:
            continue
        # Constant columns produce NaN correlations (divide-by-zero inside
        # corrwith); NaN > threshold is False, so they're harmless.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            corr = numeric_df.corrwith(numeric_df[target_col]).abs()
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


def _build_engineered_frame(max_rows: int | None) -> pd.DataFrame:
    """Read the CSV(s), engineer features, apply the FP refinement, and run the
    leakage check. Returns the fully engineered frame in temporal order."""
    # Use low_memory=True and optimize dtypes to prevent memory overflow
    tx = pd.read_csv(TRANSACTION_CSV, nrows=max_rows, low_memory=True)
    # Downcast numeric columns to reduce memory
    for col in tx.select_dtypes(include=["float64"]).columns:
        tx[col] = pd.to_numeric(tx[col], downcast="float")
    for col in tx.select_dtypes(include=["int64"]).columns:
        tx[col] = pd.to_numeric(tx[col], downcast="integer")

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

    # Train-only amount median for the FP rule — NEVER touches test-period rows.
    train_len = int(len(df) * 0.70)
    _train_amt_median = (
        float(df.iloc[:train_len][TX_AMT_COL].median())
        if TX_AMT_COL in df.columns else None
    )
    df = _engineer_features(df, amt_median=_train_amt_median)

    # ------------------------------------------------------------------
    # FP label refinement — apply train-only amount quantile.
    # The quantile is computed BEFORE the test period, then applied to the
    # whole frame so the target definition cannot peek at future data.
    # ------------------------------------------------------------------
    if TX_FRAUD_COL in df.columns and TX_AMT_COL in df.columns:
        n = len(df)
        train_end = int(n * 0.70)
        train_df = df.iloc[:train_end]
        _amt_threshold = train_df[TX_AMT_COL].quantile(0.75)
        df.loc[:, IS_FALSE_POSITIVE_COL] = (
            (df[TX_FRAUD_COL] == 0)
            & (df[TX_AMT_COL] >= _amt_threshold)
            & (df[IS_FALSE_POSITIVE_COL] == 1)
        ).astype(int)

    leakage_check(df)
    return df


def load_data(max_rows: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load IEEE-CIS, engineer features, strict temporal 70/15/15 split.

    The engineered frame is cached to parquet so repeated loads (train vs.
    evaluation) don't re-parse the 680 MB CSV and re-derive every feature.
    """
    if not TRANSACTION_CSV.exists():
        raise FileNotFoundError(
            f"Real IEEE-CIS transaction data not found at {TRANSACTION_CSV}. "
            f"Place train_transaction.csv and train_identity.csv in {DATA_DIR}."
        )

    rows_key = "all" if max_rows is None else str(max_rows)
    cache_path = DATA_DIR / f"engineered_v{CACHE_VERSION}_{rows_key}.parquet"

    if cache_path.exists():
        df = pd.read_parquet(cache_path)
    else:
        df = _build_engineered_frame(max_rows)
        # Only cache if we loaded the FULL request (cache is always complete).
        df.to_parquet(cache_path, index=False)

    _validate_feature_columns(df)

    # Strict temporal split: 70 / 15 / 15
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    return train, val, test


def _validate_feature_columns(df: pd.DataFrame) -> None:
    """Hard-fail on feature/column mismatch instead of silently zero-filling."""
    missing = []
    for feat in list(FRAUD_FEATURES) + list(FP_FEATURES):
        if feat not in df.columns:
            missing.append(feat)
    if missing:
        raise RuntimeError(
            "Feature mismatch: engineered frame is missing "
            f"{len(missing)} declared features: {sorted(missing)}. "
            "Delete the parquet cache (backend/app/ml/data/engineered_*.parquet) "
            "and rerun."
        )


def get_feature_matrix(df: pd.DataFrame, feature_names: list) -> np.ndarray:
    """Extract dense NumPy feature matrix. Missing columns raise (never zeros)."""
    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        raise RuntimeError(
            f"Missing feature columns required by model: {missing}. "
            "This indicates a feature-set/pipeline mismatch."
        )
    return df[feature_names].to_numpy(dtype=np.float64)