from __future__ import annotations

import pandas as pd

from ha_data_analytics.azure_blob import EntitySeries, SensorBlob


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
