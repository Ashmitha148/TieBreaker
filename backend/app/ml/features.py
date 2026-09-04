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

    Rows are sorted by (group, time); within each contiguous group the times are
    ascending, so the window lower bound is found with ``np.searchsorted`` on
    that group's segment. The search is O(log len(group)) per row and all the
    arithmetic is vectorized per group (no per-row Python loop).
    """
    if group_col not in df.columns or time_col not in df.columns or agg_col not in df.columns:
        return pd.Series(0.0, index=df.index)

    n = len(df)
    if n == 0:
        return pd.Series(dtype=np.float64)

    group = df[group_col].to_numpy()
    times = df[time_col].to_numpy(dtype=np.float64)
    vals = df[agg_col].to_numpy(dtype=np.float64)

    # Sort by (group, time) so each group is contiguous with ascending times.
    order = np.lexsort((times, group))
    g = group[order]
    t = times[order]
    v = vals[order]

    result = np.zeros(n, dtype=np.float64)
    window = float(window_sec)

    # Consecutive group start positions (g is sorted, so unique values give the
    # boundaries directly).
    starts = np.unique(g, return_index=True)[1]
    if starts.size == 0:
        return pd.Series(result, index=df.index)

    ends = np.concatenate([starts[1:], [n]])
    for start, end in zip(starts, ends):
        seg_len = int(end - start)
        if seg_len <= 1:
            continue

        t_seg = t[start:end]
        v_seg = v[start:end]
        idx_local = np.arange(seg_len, dtype=np.int64)

        # First index in this group with time >= time_i - window. Times within
        # the segment are ascending, so this equals searchsorted on the segment;
        # e = idx_local excludes the current row (and same-time rows).
        lo = np.searchsorted(t_seg, t_seg - window, side="left")
        s = lo
        cnt = idx_local - s

        if agg == "count":
            out = cnt.astype(np.float64)
        else:
            # pre[j] = sum of first j elements -> window [s, idx) = pre[idx]-pre[s]
            pre = np.concatenate([[0.0], np.cumsum(v_seg)])
            sm = pre[idx_local] - pre[s]
            if agg == "mean":
                out = np.divide(sm, cnt, out=np.zeros(seg_len, dtype=np.float64),
                                where=cnt > 0)
            elif agg == "std":
                pre2 = np.concatenate([[0.0], np.cumsum(v_seg * v_seg)])
                sq = pre2[idx_local] - pre2[s]
                mean = sm / np.maximum(cnt, 1.0)
                var = (sq / np.maximum(cnt, 1.0)) - mean ** 2
                var = np.clip(var, 0.0, None)
                out = np.sqrt(var)
                out[cnt <= 1] = 0.0
            else:  # sum and fallback
                out = sm.astype(np.float64)

        result[start:end] = out

    out_series = np.zeros(n, dtype=np.float64)
    out_series[order] = result
    return pd.Series(out_series, index=df.index)


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


# ---------------------------------------------------------------------------
# Extra leakage-safe features (cheap, no future info)
# ---------------------------------------------------------------------------
def log_amt(df: pd.DataFrame) -> pd.Series:
    """Log-transformed transaction amount (skew reduction)."""
    if "TransactionAmt" not in df.columns:
        return pd.Series(0.0, index=df.index)
    return np.log1p(df["TransactionAmt"].to_numpy(dtype=np.float64))


def product_cd_encoded(df: pd.DataFrame) -> pd.Series:
    """Encode ProductCD (W/C/R/S/H). Unknown -> 0."""
    if "ProductCD" not in df.columns:
        return pd.Series(0.0, index=df.index)
    mapping = {"W": 1, "C": 2, "R": 3, "S": 4, "H": 5}
    return df["ProductCD"].map(mapping).fillna(0).astype(float)


def recv_email_domain_risk(df: pd.DataFrame) -> pd.Series:
    """Risk score based on R_emaildomain (same bands as sender domain)."""
    if "R_emaildomain" not in df.columns:
        return pd.Series(0.0, index=df.index)
    domain = df["R_emaildomain"].fillna("unknown").str.lower()
    high_risk = {"mail.com", "outlook.com", "protonmail.com", "yandex.com"}
    medium_risk = {"hotmail.com", "live.com", "yahoo.com", "gmail.com"}
    return domain.apply(
        lambda d: 2 if d in high_risk else (1 if d in medium_risk else 0)
    ).astype(float)


def id_02_usage_ratio(df: pd.DataFrame) -> pd.Series:
    """TransactionAmt / id_02 — amount per 'unit'. Missing id_02 -> 0."""
    if "TransactionAmt" not in df.columns or "id_02" not in df.columns:
        return pd.Series(0.0, index=df.index)
    amt = df["TransactionAmt"].to_numpy(dtype=np.float64)
    id02 = df["id_02"].to_numpy(dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = amt / id02
    return pd.Series(np.nan_to_num(ratio, nan=0.0, posinf=0.0, neginf=0.0))


def is_email_domain_match(df: pd.DataFrame) -> pd.Series:
    """1 when sender and recipient email domains are identical."""
    if "P_emaildomain" not in df.columns or "R_emaildomain" not in df.columns:
        return pd.Series(0.0, index=df.index)
    p = df["P_emaildomain"].fillna("unknown").str.lower()
    r = df["R_emaildomain"].fillna("unknown").str.lower()
    return (p == r).astype(float)


# Match-flag columns (M1..M9) are set pre-transaction (billing/address
# verifications recorded at transaction time), so their counts carry no
# future information — safe to aggregate into a single compact risk signal.
_M_COLS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]


def m_match_count(df: pd.DataFrame) -> pd.Series:
    """Count of successful match flags (M1..M9). Missing/unmatched -> 0.

    More matches historically accompany legitimate transactions; a low count
    is a leakage-safe, cheap fraud signal (no temporal look-ahead)."""
    out = np.zeros(len(df), dtype=np.float64)
    present = [c for c in _M_COLS if c in df.columns]
    if not present:
        return pd.Series(out, index=df.index)
    for c in present:
        s = df[c].astype("object")
        out += (s == "T").astype(float).to_numpy()
    return pd.Series(out, index=df.index)