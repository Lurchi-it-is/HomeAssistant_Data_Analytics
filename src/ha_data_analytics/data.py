from __future__ import annotations

from io import BytesIO
from typing import Literal

import pandas as pd

Aggregation = Literal["mean", "min", "max", "sum", "count"]

TIME_COLUMNS = ("timestamp_local", "timestamp_utc", "changed_utc", "updated_utc")
RESAMPLE_RULES = {
    "Keine": None,
    "Minute": "min",
    "Stunde": "h",
    "Tag": "D",
}


def parse_homeassistant_csv(content: bytes, sensor_name: str) -> pd.DataFrame:
    df = pd.read_csv(BytesIO(content))
    df.columns = [str(column).strip() for column in df.columns]

    timestamp = _build_timestamp(df)
    if timestamp.isna().all():
        raise ValueError("Keine verwertbare Zeitspalte gefunden.")

    if "state" not in df.columns:
        raise ValueError("Die CSV-Datei enthaelt keine Spalte 'state'.")

    result = df.copy()
    result["sensor"] = sensor_name
    result["timestamp"] = timestamp
    result["state_text"] = result["state"].astype("string")
    result["state_numeric"] = pd.to_numeric(result["state"], errors="coerce")
    result = result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return result


def filter_by_time(
    df: pd.DataFrame,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if start is not None:
        filtered = filtered[filtered["timestamp"] >= _normalize_timestamp(start)]
    if end is not None:
        filtered = filtered[filtered["timestamp"] <= _normalize_timestamp(end)]
    return filtered.reset_index(drop=True)


def resample_data(
    df: pd.DataFrame,
    rule: str | None,
    aggregation: Aggregation = "mean",
) -> pd.DataFrame:
    if not rule:
        return df.copy()
    if df.empty:
        return df.copy()

    indexed = df.set_index("timestamp").sort_index()
    if aggregation == "count":
        series = indexed["state_text"].resample(rule).count()
    else:
        series = getattr(indexed["state_numeric"].resample(rule), aggregation)()

    resampled = series.dropna().reset_index(name="state_numeric")
    resampled["state"] = resampled["state_numeric"]
    resampled["state_text"] = resampled["state_numeric"].astype("string")
    resampled["sensor"] = df["sensor"].iloc[0] if "sensor" in df.columns and not df.empty else ""
    return resampled


def filter_and_resample(
    df: pd.DataFrame,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    rule: str | None,
    aggregation: Aggregation,
) -> pd.DataFrame:
    return resample_data(filter_by_time(df, start, end), rule, aggregation)


def _build_timestamp(df: pd.DataFrame) -> pd.Series:
    timestamp = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    for column in TIME_COLUMNS:
        if column not in df.columns:
            continue
        parsed = pd.to_datetime(df[column], errors="coerce", utc=column.endswith("_utc"))
        if getattr(parsed.dt, "tz", None) is not None:
            parsed = parsed.dt.tz_convert(None)
        timestamp = timestamp.fillna(parsed)
    return timestamp


def _normalize_timestamp(value: pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        return timestamp.tz_convert(None)
    return timestamp
