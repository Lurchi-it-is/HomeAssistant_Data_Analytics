from __future__ import annotations

import pandas as pd
import pytest

from ha_data_analytics.data import filter_and_resample, parse_homeassistant_csv, total_delta_by_period


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


def test_total_delta_by_period_calculates_daily_values_per_entity() -> None:
    first = parse_homeassistant_csv(
        (
            "timestamp_local,state\n"
            "2026-05-01 00:05:00,100\n"
            "2026-05-01 23:55:00,115\n"
            "2026-05-02 00:10:00,115\n"
            "2026-05-02 23:50:00,140\n"
        ).encode(),
        "sensor.total_energy",
    )
    second = parse_homeassistant_csv(
        (
            "timestamp_local,state\n"
            "2026-05-01 01:00:00,50\n"
            "2026-05-01 22:00:00,53\n"
        ).encode(),
        "sensor.total_water",
    )

    result = total_delta_by_period(pd.concat([first, second], ignore_index=True), "D")

    values = {
        (row.sensor, row.timestamp): row.state_numeric
        for row in result.itertuples(index=False)
    }
    assert values[("sensor.total_energy", pd.Timestamp("2026-05-01"))] == pytest.approx(15)
    assert values[("sensor.total_energy", pd.Timestamp("2026-05-02"))] == pytest.approx(25)
    assert values[("sensor.total_water", pd.Timestamp("2026-05-01"))] == pytest.approx(3)


def test_total_delta_by_period_ignores_negative_counter_resets() -> None:
    df = parse_homeassistant_csv(
        (
            "timestamp_local,state\n"
            "2026-05-01 00:00:00,100\n"
            "2026-05-01 23:00:00,10\n"
        ).encode(),
        "sensor.resetting_total",
    )

    result = total_delta_by_period(df, "D")

    assert result.empty


def test_filter_and_resample_uses_daily_total_delta_as_default_period() -> None:
    df = parse_homeassistant_csv(
        (
            "timestamp_local,state\n"
            "2026-05-01 00:00:00,10\n"
            "2026-05-01 23:00:00,17\n"
        ).encode(),
        "sensor.total",
    )

    result = filter_and_resample(df, None, None, None, "mean", "total_delta")

    assert len(result) == 1
    assert result.loc[0, "state_numeric"] == pytest.approx(7)
