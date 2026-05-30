from __future__ import annotations

from io import BytesIO
from typing import Literal

import pandas as pd

Aggregation = Literal["mean", "min", "max", "sum", "count"]
ValueMode = Literal["raw", "total_delta", "total_period_progress"]

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

    frames: list[pd.DataFrame] = []
    for sensor, group in df.groupby("sensor", dropna=False):
        indexed = group.set_index("timestamp").sort_index()
        if aggregation == "count":
            series = indexed["state_text"].resample(rule).count()
        else:
            series = getattr(indexed["state_numeric"].resample(rule), aggregation)()

        resampled = series.dropna().reset_index(name="state_numeric")
        resampled["state"] = resampled["state_numeric"]
        resampled["state_text"] = resampled["state_numeric"].astype("string")
        resampled["sensor"] = sensor
        frames.append(resampled)

    if not frames:
        return df.head(0).copy()
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor"]).reset_index(drop=True)


def filter_and_resample(
    df: pd.DataFrame,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    rule: str | None,
    aggregation: Aggregation,
    value_mode: ValueMode = "raw",
) -> pd.DataFrame:
    filtered = filter_by_time(df, start, end)
    if value_mode == "total_delta":
        return total_delta_by_period(filtered, rule or "D")
    if value_mode == "total_period_progress":
        return total_progress_by_period(filtered, rule or "D")
    return resample_data(filtered, rule, aggregation)


def filter_and_resample_by_entity_modes(
    df: pd.DataFrame,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    rule: str | None,
    aggregation: Aggregation,
    entity_value_modes: dict[str, str],
    default_value_mode: ValueMode = "raw",
) -> pd.DataFrame:
    filtered = filter_by_time(df, start, end)
    if filtered.empty:
        return filtered

    frames: list[pd.DataFrame] = []
    for sensor, group in filtered.groupby("sensor", dropna=False):
        mode = entity_value_modes.get(str(sensor), default_value_mode)
        if mode == "total_delta":
            frames.append(total_delta_by_period(group, rule or "D"))
        elif mode == "total_period_progress":
            frames.append(total_progress_by_period(group, rule or "D"))
        else:
            frames.append(resample_data(group, rule, aggregation))

    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return filtered.head(0).copy()
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor"]).reset_index(drop=True)


def total_delta_by_period(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    frames: list[pd.DataFrame] = []
    for sensor, group in df.dropna(subset=["state_numeric"]).groupby("sensor", dropna=False):
        indexed = group.set_index("timestamp").sort_index()
        grouped = indexed["state_numeric"].resample(rule)
        deltas = (grouped.last() - grouped.first()).dropna()
        deltas = deltas[deltas >= 0]

        frame = deltas.reset_index(name="state_numeric")
        frame["state"] = frame["state_numeric"]
        frame["state_text"] = frame["state_numeric"].astype("string")
        frame["sensor"] = sensor
        frames.append(frame)

    if not frames:
        return df.head(0).copy()
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor"]).reset_index(drop=True)


def total_progress_by_period(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    frames: list[pd.DataFrame] = []
    for sensor, group in df.dropna(subset=["state_numeric"]).groupby("sensor", dropna=False):
        indexed = group.set_index("timestamp").sort_index()
        baseline = indexed["state_numeric"].groupby(pd.Grouper(freq=rule)).transform("first")
        progress = (indexed["state_numeric"] - baseline).dropna()
        progress = progress[progress >= 0]

        frame = indexed.loc[progress.index].reset_index()
        frame["state_numeric"] = progress.to_numpy()
        frame["state"] = frame["state_numeric"]
        frame["state_text"] = frame["state_numeric"].astype("string")
        frame["sensor"] = sensor
        frames.append(frame)

    if not frames:
        return df.head(0).copy()
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor"]).reset_index(drop=True)


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
