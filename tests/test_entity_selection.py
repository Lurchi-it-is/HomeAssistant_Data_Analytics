from __future__ import annotations

import pandas as pd

from ha_data_analytics.azure_blob import EntitySeries, SensorBlob
from ha_data_analytics.entity_selection import select_blobs_for_range


def test_select_blobs_for_range_uses_overlapping_months() -> None:
    entity = EntitySeries(
        name="sensor.energy",
        blobs=(
            SensorBlob(name="sensor.energy", blob_name="energy-2026-04.csv", month="2026-04"),
            SensorBlob(name="sensor.energy", blob_name="energy-2026-05.csv", month="2026-05"),
            SensorBlob(name="sensor.energy", blob_name="energy-2026-06.csv", month="2026-06"),
        ),
    )

    selected = select_blobs_for_range(
        entity,
        pd.Timestamp("2026-05-15 12:00:00"),
        pd.Timestamp("2026-06-01 00:00:00"),
    )

    assert [blob.month for blob in selected] == ["2026-05", "2026-06"]


def test_select_blobs_for_range_keeps_unversioned_csv_files() -> None:
    entity = EntitySeries(
        name="sensor.energy",
        blobs=(SensorBlob(name="sensor.energy", blob_name="energy.csv", month=None),),
    )

    selected = select_blobs_for_range(
        entity,
        pd.Timestamp("2026-05-01"),
        pd.Timestamp("2026-05-31"),
    )

    assert [blob.blob_name for blob in selected] == ["energy.csv"]
