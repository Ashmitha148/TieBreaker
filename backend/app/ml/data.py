"""
TieBreaker data loader for real IEEE-CIS Fraud Detection dataset.

Loads train_transaction.csv and train_identity.csv, joins on TransactionID,
sorts temporally by TransactionDT, and performs a strict temporal split
(70 / 15 / 15) to prevent data leakage.

NO synthetic fallback — if real data is missing, load_data() raises
FileNotFoundError with a clear message.
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

# ---------------------------------------------------------------------------
# Feature lists used by the ML pipeline.
# These are a curated subset of IEEE-CIS columns plus engineered features.
# ---------------------------------------------------------------------------
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


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive synthetic-but-meaningful features from raw IEEE-CIS columns."""
    df = df.copy()

    # Temporal features from TransactionDT (seconds from reference)
    if TX_DT_COL in df.columns:
        df["hour_of_day"] = (df[TX_DT_COL] // 3600) % 24
        df["day_of_week"] = ((df[TX_DT_COL] // 86400) % 7).astype(int)
    else:
        df["hour_of_day"] = 12
        df["day_of_week"] = 0

    # Device change flag: proxy from identity data
    if "DeviceType" in df.columns:
        df["device_change_flag"] = (
            df["DeviceType"].isna() | (df["DeviceType"] == "")
        ).astype(int)
    elif "id_30" in df.columns:
        df["device_change_flag"] = df["id_30"].isna().astype(int)
    else:
        df["device_change_flag"] = 0

    # Geo mismatch: proxy from addr1/addr2
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

    # Fill NaNs for numeric columns used as features
    numeric_cols = [c for c in df.columns if df[c].dtype.kind in "iufc"]
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # -----------------------------------------------------------------------
    # Create FP label: legitimate transactions that look risky.
    # This is a heuristic derived from the real data itself (not synthetic).
    # -----------------------------------------------------------------------
    if TX_FRAUD_COL in df.columns:
        amt_median = (
            df[TX_AMT_COL].median() if TX_AMT_COL in df.columns else 100.0
        )
        high_amount = (
            (df[TX_AMT_COL] > amt_median * 3).astype(int)
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
            high_amount * 0.30
            + unusual_hour * 0.30
            + new_customer * 0.20
            + df["device_change_flag"] * 0.10
            + df["geo_mismatch_flag"] * 0.10
        )
        df["is_false_positive"] = (
            (df[TX_FRAUD_COL] == 0) & (fp_score > 0.50)
        ).astype(int)
    else:
        df["is_false_positive"] = 0

    return df


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load real IEEE-CIS data, join identity, engineer features,
    and perform a strict temporal 70/15/15 split.

    Raises:
        FileNotFoundError: If train_transaction.csv is not present.
        ValueError: If isFraud column is missing.
    """
    if not TRANSACTION_CSV.exists():
        raise FileNotFoundError(
            f"Real IEEE-CIS transaction data not found at {TRANSACTION_CSV}. "
            f"Place train_transaction.csv and train_identity.csv in {DATA_DIR}. "
            f"See download_dataset.py for acquisition instructions."
        )

    tx = pd.read_csv(TRANSACTION_CSV)

    if IDENTITY_CSV.exists():
        idf = pd.read_csv(IDENTITY_CSV)
        df = tx.merge(idf, on=TX_ID_COL, how="left")
    else:
        warnings.warn(
            f"Identity file not found at {IDENTITY_CSV}; "
            "proceeding with transaction data only."
        )
        df = tx.copy()

    if TX_FRAUD_COL not in df.columns:
        raise ValueError(
            f"Required column '{TX_FRAUD_COL}' not found in transaction data."
        )

    # Temporal sort — critical to prevent leakage
    if TX_DT_COL in df.columns:
        df = df.sort_values(TX_DT_COL).reset_index(drop=True)
    else:
        warnings.warn(
            f"Column '{TX_DT_COL}' not found; split may not be temporal."
        )

    df = _engineer_features(df)

    # Strict temporal split: 70 / 15 / 15
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    return train, val, test


def get_feature_matrix(df: pd.DataFrame, feature_names: list) -> np.ndarray:
    """
    Extract a dense NumPy feature matrix from a DataFrame.
    Missing columns are filled with 0 and a warning is emitted.
    """
    available = [f for f in feature_names if f in df.columns]
    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        warnings.warn(
            f"Missing feature columns (filled with 0): {missing}"
        )
    X = df[available].to_numpy(dtype=np.float64)
    if missing:
        X = np.hstack(
            [X, np.zeros((len(df), len(missing)), dtype=np.float64)]
        )
    return X
