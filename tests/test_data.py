from __future__ import annotations

import pandas as pd
import pytest

from ha_data_analytics.data import filter_and_resample, parse_homeassistant_csv


def test_parse_homeassistant_csv_with_numeric_state() -> None:
    content = (
        "timestamp_utc,timestamp_local,state,changed_utc,updated_utc\n"
        '2026-05-01T04:49:07.855Z,"2026-05-01 06:49:07",0.005,,"2026-05-01 04:49:07"\n'
    ).encode()

    df = parse_homeassistant_csv(content, "sensor.energy")

    assert list(df["sensor"]) == ["sensor.energy"]
    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-05-01 06:49:07")
    assert df.loc[0, "state_text"] == "0.005"
    assert df.loc[0, "state_numeric"] == pytest.approx(0.005)


def test_parse_homeassistant_csv_keeps_non_numeric_state() -> None:
    content = (
        "timestamp_utc,timestamp_local,state,changed_utc,updated_utc\n"
        "2026-05-01T04:49:07.855Z,,on,,\n"
    ).encode()

    df = parse_homeassistant_csv(content, "binary.sensor")

    assert df.loc[0, "state_text"] == "on"
    assert pd.isna(df.loc[0, "state_numeric"])
    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-05-01 04:49:07.855")


def test_parse_homeassistant_csv_uses_updated_utc_as_time_fallback() -> None:
    content = (
        "timestamp_utc,timestamp_local,state,changed_utc,updated_utc\n"
        ",,42,,2026-05-01 04:49:07\n"
    ).encode()

    df = parse_homeassistant_csv(content, "sensor.fallback")

    assert df.loc[0, "timestamp"] == pd.Timestamp("2026-05-01 04:49:07")


def test_resample_data_by_hour_mean_after_time_filter() -> None:
    content = (
        "timestamp_local,state\n"
        "2026-05-01 06:00:00,1\n"
        "2026-05-01 06:30:00,3\n"
        "2026-05-01 07:00:00,10\n"
    ).encode()
    df = parse_homeassistant_csv(content, "sensor.power")

    result = filter_and_resample(
        df,
        pd.Timestamp("2026-05-01 06:00:00"),
        pd.Timestamp("2026-05-01 06:59:59"),
        "h",
        "mean",
    )

    assert len(result) == 1
    assert result.loc[0, "state_numeric"] == pytest.approx(2.0)


def test_resample_data_keeps_entities_separate() -> None:
    first = parse_homeassistant_csv(
        b"timestamp_local,state\n2026-05-01 06:00:00,1\n2026-05-01 06:30:00,3\n",
        "sensor.first",
    )
    second = parse_homeassistant_csv(
        b"timestamp_local,state\n2026-05-01 06:00:00,10\n2026-05-01 06:30:00,20\n",
        "sensor.second",
    )

    result = filter_and_resample(
        pd.concat([first, second], ignore_index=True),
        None,
        None,
        "h",
        "mean",
    )

    values = dict(zip(result["sensor"], result["state_numeric"], strict=True))
    assert values == {"sensor.first": pytest.approx(2.0), "sensor.second": pytest.approx(15.0)}
