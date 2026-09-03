"""Engineered risk features for the TieBreaker ML pipeline.

Every function returns a ``pd.Series`` aligned 1:1 with the **original**
``df.index`` (same length, same order), regardless of any internal
sorting/grouping performed to compute the feature. Series are float (or int)
and NaN-free so they can be stacked directly into a feature matrix.
"""

import numpy as np
import pandas as pd

# 7-day window in seconds (IEEE-CIS TransactionDT is seconds from a reference).
SEVEN_DAYS_SECONDS = 7 * 24 * 3600


def velocity_7d_trend(df: pd.DataFrame) -> pd.Series:
    """Count of the customer's (card1) transactions in the trailing 7-day
    window, *including* the current transaction.

    Implemented as a true time-based rolling window (not a rolling count of
    the previous 7 rows), so irregular transaction gaps are handled correctly.
    """
    if "TransactionDT" not in df.columns or "card1" not in df.columns:
        return pd.Series(0.0, index=df.index)

    tmp = pd.DataFrame(
        {
            "card1": df["card1"].values,
            "dt": pd.to_timedelta(df["TransactionDT"].values, unit="s"),
            "_row": np.arange(len(df)),
        }
    )
    # Sort by (card1, time) so the grouped rolling window walks each
    # customer's history chronologically; remember the original row position.
    tmp_sorted = tmp.sort_values(["card1", "dt"]).set_index("dt")
    counts = tmp_sorted.groupby("card1")["_row"].rolling("7D").count()
    # groupby(...).rolling() preserves tmp_sorted's row order (groups are
    # processed in sorted order), so values align positionally.
    out = np.empty(len(df), dtype=np.float64)
    out[tmp_sorted["_row"].values] = counts.values
    return pd.Series(out, index=df.index)


def merchant_chargeback_rate(df: pd.DataFrame) -> pd.Series:
    """Merchant chargeback rate placeholder.

    IEEE-CIS carries no chargeback data, so this stays 0.0 until an external
    chargeback feed is joined on the merchant key. Deliberately *not* derived
    from ``isFraud`` — that would be target leakage.
    """
    return pd.Series(0.0, index=df.index)


def payment_method_risk_score(df: pd.DataFrame) -> pd.Series:
    """Weighted risk score from the encoded card4/card6 columns."""
    card4_risk = df.get("card4_encoded", pd.Series(0.0, index=df.index))
    card6_risk = df.get("card6_encoded", pd.Series(0.0, index=df.index))
    return (card4_risk * 0.6 + card6_risk * 0.4).astype(float)


def hours_since_last_txn(df: pd.DataFrame) -> pd.Series:
    """Hours since the customer's (card1) previous transaction.

    First-ever transactions get a large sentinel (999999) meaning "no
    history". Negative gaps are impossible on a chronological diff, but clip
    defensively anyway.
    """
    if "TransactionDT" not in df.columns or "card1" not in df.columns:
        return pd.Series(999999.0, index=df.index)

    tmp = pd.DataFrame(
        {
            "card1": df["card1"].values,
            "dt": df["TransactionDT"].values,
            "_row": np.arange(len(df)),
        }
    ).sort_values(["card1", "dt"])
    diff = tmp.groupby("card1")["dt"].diff().clip(lower=0)
    hours = (diff / 3600.0).fillna(999999.0)
    out = np.empty(len(df), dtype=np.float64)
    out[tmp["_row"].values] = hours.values
    return pd.Series(out, index=df.index)


def hour_bin_risk(df: pd.DataFrame) -> pd.Series:
    """Late night (0-5) = highest risk (2), early morning (6-11) = medium (1), else low (0)."""
    hour = df.get("hour_of_day", pd.Series(12, index=df.index))
    return hour.apply(lambda h: 2 if h <= 5 else (1 if h <= 11 else 0)).astype(float)


def amount_zscore(df: pd.DataFrame) -> pd.Series:
    """Z-score of amount relative to the customer's (card1) mean/std.

    Note: computed on the frame it is given — ``load_data`` engineers features
    before the temporal split, so this is an unsupervised normalisation (no
    target information), which keeps it leakage-safe.
    """
    if "TransactionAmt" not in df.columns or "card1" not in df.columns:
        return pd.Series(0.0, index=df.index)

    customer_mean = df.groupby("card1")["TransactionAmt"].transform("mean")
    customer_std = df.groupby("card1")["TransactionAmt"].transform("std").fillna(1)
    # Avoid division by 0 if std is 0 (single-transaction customers)
    customer_std = customer_std.replace(0, 1)
    return ((df["TransactionAmt"] - customer_mean) / customer_std).fillna(0.0)


def weekend_flag(df: pd.DataFrame) -> pd.Series:
    """Saturday (5) and Sunday (6) = higher risk."""
    dow = df.get("day_of_week", pd.Series(0, index=df.index))
    return dow.apply(lambda d: 1 if d in [5, 6] else 0).astype(float)
