"""Engineered risk features for TieBreaker — V2 (leakage-safe).

CRITICAL FIXES from V1:
1. All temporal windows are PAST-ONLY (closed='left', current row excluded).
2. amount_zscore uses expanding mean/std with .shift(1) — never future data.
3. velocity_7d_trend renamed to velocity_7d_count for clarity; excludes current row.
4. New features: 1h/24h velocity, email domain risk, device/browser encoding.

Every function returns a pd.Series aligned 1:1 with df.index.
"""

import numpy as np
import pandas as pd

SEVEN_DAYS_SECONDS = 7 * 24 * 3600
ONE_DAY_SECONDS = 24 * 3600
ONE_HOUR_SECONDS = 3600


def _temporal_rolling(df: pd.DataFrame, group_col: str, time_col: str,
                      agg_col: str, window_sec: int, agg: str) -> pd.Series:
    """Leakage-safe temporal rolling aggregation. Each row sees ONLY past
    transactions within [time - window, time) — current row EXCLUDED.

    Uses vectorized searchsorted + cumsum for O(n log n) per group.
    """
    if group_col not in df.columns or time_col not in df.columns or agg_col not in df.columns:
        return pd.Series(0.0, index=df.index)

    tmp = df[[group_col, time_col, agg_col]].copy()
    tmp["_row"] = np.arange(len(df))
    tmp = tmp.sort_values([group_col, time_col])

    result = np.zeros(len(df), dtype=np.float64)

    for _, group in tmp.groupby(group_col, sort=False):
        if len(group) == 0:
            continue
        times = group[time_col].values
        vals = group[agg_col].values
        rows = group["_row"].values
        n = len(group)

        # For each position i, find first index with time >= times[i] - window
        left_bounds = times - window_sec
        start_idx = np.searchsorted(times, left_bounds, side="left")

        # Cumulative sums for O(1) range queries
        cumsum = np.cumsum(vals)
        cumsum_sq = np.cumsum(vals ** 2)

        for i in range(n):
            s, e = start_idx[i], i  # e = i excludes current row
            if s >= e:
                result[rows[i]] = 0.0
                continue
            cnt = e - s
            sm = cumsum[e - 1] - (cumsum[s - 1] if s > 0 else 0.0)

            if agg == "count":
                result[rows[i]] = float(cnt)
            elif agg == "sum":
                result[rows[i]] = float(sm)
            elif agg == "mean":
                result[rows[i]] = float(sm / cnt)
            elif agg == "std":
                if cnt > 1:
                    sq = cumsum_sq[e - 1] - (cumsum_sq[s - 1] if s > 0 else 0.0)
                    mean = sm / cnt
                    var = max((sq / cnt) - mean ** 2, 0.0)
                    result[rows[i]] = float(np.sqrt(var))
                else:
                    result[rows[i]] = 0.0
            else:
                result[rows[i]] = float(sm / cnt)

    return pd.Series(result, index=df.index)


# ---------------------------------------------------------------------------
# Velocity features — all past-only
# ---------------------------------------------------------------------------
def velocity_1h_count(df: pd.DataFrame) -> pd.Series:
    """Customer (card1) txn count in last 1h, EXCLUDING current."""
    return _temporal_rolling(df, "card1", "TransactionDT", "TransactionAmt", ONE_HOUR_SECONDS, "count")


def velocity_24h_count(df: pd.DataFrame) -> pd.Series:
    """Customer (card1) txn count in last 24h, EXCLUDING current."""
    return _temporal_rolling(df, "card1", "TransactionDT", "TransactionAmt", ONE_DAY_SECONDS, "count")


def velocity_7d_count(df: pd.DataFrame) -> pd.Series:
    """Customer (card1) txn count in last 7d, EXCLUDING current."""
    return _temporal_rolling(df, "card1", "TransactionDT", "TransactionAmt", SEVEN_DAYS_SECONDS, "count")


def velocity_24h_amount_sum(df: pd.DataFrame) -> pd.Series:
    """Customer (card1) total amount in last 24h, EXCLUDING current."""
    return _temporal_rolling(df, "card1", "TransactionDT", "TransactionAmt", ONE_DAY_SECONDS, "sum")


def velocity_24h_amount_mean(df: pd.DataFrame) -> pd.Series:
    """Customer (card1) mean amount in last 24h, EXCLUDING current."""
    return _temporal_rolling(df, "card1", "TransactionDT", "TransactionAmt", ONE_DAY_SECONDS, "mean")


# ---------------------------------------------------------------------------
# Historical count features — past-only
# ---------------------------------------------------------------------------
def card1_total_count(df: pd.DataFrame) -> pd.Series:
    """Total past txns for this card1 before current txn."""
    return _temporal_rolling(df, "card1", "TransactionDT", "TransactionAmt", 999999999, "count")


def addr1_total_count(df: pd.DataFrame) -> pd.Series:
    """Total past txns for this addr1 before current txn."""
    return _temporal_rolling(df, "addr1", "TransactionDT", "TransactionAmt", 999999999, "count")


# ---------------------------------------------------------------------------
# Simple features
# ---------------------------------------------------------------------------
def merchant_chargeback_rate(df: pd.DataFrame) -> pd.Series:
    """Placeholder — stays 0 until external chargeback feed is joined."""
    return pd.Series(0.0, index=df.index)


def payment_method_risk_score(df: pd.DataFrame) -> pd.Series:
    """Weighted risk from card4/card6 encoding."""
    card4_risk = df.get("card4_encoded", pd.Series(0.0, index=df.index))
    card6_risk = df.get("card6_encoded", pd.Series(0.0, index=df.index))
    return (card4_risk * 0.6 + card6_risk * 0.4).astype(float)


def hours_since_last_txn(df: pd.DataFrame) -> pd.Series:
    """Hours since customer's (card1) previous transaction."""
    if "TransactionDT" not in df.columns or "card1" not in df.columns:
        return pd.Series(999999.0, index=df.index)
    tmp = pd.DataFrame({
        "card1": df["card1"].values,
        "dt": df["TransactionDT"].values,
        "_row": np.arange(len(df)),
    }).sort_values(["card1", "dt"])
    diff = tmp.groupby("card1")["dt"].diff().clip(lower=0)
    hours = (diff / 3600.0).fillna(999999.0)
    out = np.empty(len(df), dtype=np.float64)
    out[tmp["_row"].values] = hours.values
    return pd.Series(out, index=df.index)


def hour_bin_risk(df: pd.DataFrame) -> pd.Series:
    """Late night (0-5)=2, early morning (6-11)=1, else=0."""
    hour = df.get("hour_of_day", pd.Series(12, index=df.index))
    return hour.apply(lambda h: 2 if h <= 5 else (1 if h <= 11 else 0)).astype(float)


def amount_zscore_temporal(df: pd.DataFrame) -> pd.Series:
    """Z-score of amount vs customer's PAST mean/std (leakage-safe).

    FIX: Uses expanding statistics with .shift(1) so each row only sees
    transactions that occurred BEFORE it chronologically.
    """
    if "TransactionAmt" not in df.columns or "card1" not in df.columns:
        return pd.Series(0.0, index=df.index)

    tmp = pd.DataFrame({
        "card1": df["card1"].values,
        "dt": df["TransactionDT"].values,
        "amt": df["TransactionAmt"].values,
        "_row": np.arange(len(df)),
    }).sort_values(["card1", "dt"])

    grp = tmp.groupby("card1")["amt"]
    # Expanding mean/std, then shift(1) to exclude current row
    tmp["mean"] = grp.expanding().mean().shift(1).values
    tmp["std"] = grp.expanding().std().shift(1).values
    tmp["std"] = tmp["std"].fillna(1).replace(0, 1)
    tmp["zscore"] = ((tmp["amt"] - tmp["mean"]) / tmp["std"]).fillna(0.0)

    out = np.empty(len(df), dtype=np.float64)
    out[tmp["_row"].values] = tmp["zscore"].values
    return pd.Series(out, index=df.index)


def weekend_flag(df: pd.DataFrame) -> pd.Series:
    """Saturday(5) and Sunday(6) = 1."""
    dow = df.get("day_of_week", pd.Series(0, index=df.index))
    return dow.apply(lambda d: 1 if d in [5, 6] else 0).astype(float)


def email_domain_risk(df: pd.DataFrame) -> pd.Series:
    """Risk score based on P_emaildomain."""
    if "P_emaildomain" not in df.columns:
        return pd.Series(0.0, index=df.index)
    domain = df["P_emaildomain"].fillna("unknown").str.lower()
    high_risk = {"mail.com", "outlook.com", "protonmail.com", "yandex.com"}
    medium_risk = {"hotmail.com", "live.com", "yahoo.com", "gmail.com"}
    return domain.apply(lambda d: 2 if d in high_risk else (1 if d in medium_risk else 0)).astype(float)


def device_type_encoded(df: pd.DataFrame) -> pd.Series:
    """Encode DeviceType: mobile=1, desktop=2, unknown=0."""
    if "DeviceType" not in df.columns:
        return pd.Series(0.0, index=df.index)
    dt = df["DeviceType"].fillna("unknown").str.lower()
    mapping = {"mobile": 1, "desktop": 2}
    return dt.map(mapping).fillna(0).astype(float)


def browser_risk(df: pd.DataFrame) -> pd.Series:
    """Risk from id_31 (browser)."""
    if "id_31" not in df.columns:
        return pd.Series(0.0, index=df.index)
    browser = df["id_31"].fillna("unknown").str.lower()
    high = {"samsung browser", "android browser", "ie", "edge"}
    return browser.apply(lambda b: 1 if any(h in b for h in high) else 0).astype(float)


def screen_size_risk(df: pd.DataFrame) -> pd.Series:
    """Risk from id_33 (screen resolution). Missing = high risk."""
    if "id_33" not in df.columns:
        return pd.Series(1.0, index=df.index)
    return df["id_33"].isna().astype(float)


def transaction_count_by_card1_hour(df: pd.DataFrame) -> pd.Series:
    """How many times this card1 has transacted in this same hour-of-day historically."""
    if "card1" not in df.columns or "hour_of_day" not in df.columns:
        return pd.Series(0.0, index=df.index)
    tmp = df[["card1", "hour_of_day"]].copy()
    tmp["_row"] = np.arange(len(df))
    tmp = tmp.sort_values(["card1", "hour_of_day"])
    tmp["count"] = tmp.groupby(["card1", "hour_of_day"]).cumcount()
    out = np.empty(len(df), dtype=np.float64)
    out[tmp["_row"].values] = tmp["count"].values
    return pd.Series(out, index=df.index)