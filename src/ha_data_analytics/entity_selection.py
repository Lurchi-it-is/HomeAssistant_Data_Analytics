from __future__ import annotations

import pandas as pd

from ha_data_analytics.azure_blob import EntitySeries, SensorBlob


def available_datetime_range(
    entities: list[EntitySeries],
    now: pd.Timestamp | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    periods = [
        pd.Period(blob.month, freq="M")
        for entity in entities
        for blob in entity.blobs
        if blob.month is not None
    ]
    if not periods:
        return None

    start = min(period.start_time for period in periods)
    end = max(period.end_time for period in periods)
    current = (now or pd.Timestamp.now()).floor("min")
    if current < start:
        return start, end
    return start, min(end, current)


def select_blobs_for_range(
    entity: EntitySeries,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> list[SensorBlob]:
    selected: list[SensorBlob] = []
    for blob in entity.blobs:
        if blob.month is None or _month_overlaps_range(blob.month, start, end):
            selected.append(blob)
    return selected


def _month_overlaps_range(
    month: str,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> bool:
    period = pd.Period(month, freq="M")
    month_start = period.start_time
    month_end = period.end_time

    if start is not None and month_end < _normalize(start):
        return False
    if end is not None and month_start > _normalize(end):
        return False
    return True


def _normalize(value: pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        return timestamp.tz_convert(None)
    return timestamp
