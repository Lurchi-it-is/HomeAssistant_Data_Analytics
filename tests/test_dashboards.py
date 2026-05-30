from __future__ import annotations

from ha_data_analytics.dashboards import (
    Dashboard,
    DashboardStore,
    WidgetConfig,
    chart_type_index,
    filter_entity_names,
    slugify,
)


def test_dashboard_store_roundtrip(tmp_path) -> None:
    store = DashboardStore(tmp_path)
    dashboard = Dashboard(
        name="Energie Analyse",
        widgets=[
            WidgetConfig(
                sensor_blob="energy.csv",
                sensor_name="energy",
                chart_type="Linie",
                title="Energie",
                aggregation="mean",
                resample_rule="h",
                value_mode="total_delta",
            )
        ],
    )

    path = store.save(dashboard)
    loaded = store.load("energie-analyse")

    assert path.name == "energie-analyse.json"
    assert store.list_dashboards() == ["energie-analyse"]
    assert loaded.name == "Energie Analyse"
    assert loaded.widgets[0].sensor_blob == "energy.csv"
    assert loaded.widgets[0].chart_type == "Linie"
    assert loaded.widgets[0].value_mode == "total_delta"


def test_dashboard_store_delete(tmp_path) -> None:
    store = DashboardStore(tmp_path)
    store.save(Dashboard(name="Test"))

    store.delete("test")

    assert store.list_dashboards() == []


def test_slugify_limits_names_to_file_safe_values() -> None:
    assert slugify("  Mein Dashboard! 2026  ") == "mein-dashboard-2026"


def test_chart_type_index_returns_matching_index_or_default() -> None:
    assert chart_type_index("Linie") == 2
    assert chart_type_index("Unbekannt") == 0


def test_filter_entity_names_matches_all_search_terms_case_insensitive() -> None:
    names = [
        "sensor.comfoair_bridge_exhaust_air_temp",
        "sensor.comfoair_bridge_supply_air_temp",
        "sensor.backup_ampel",
    ]

    result = filter_entity_names(names, "COMFOAIR temp")

    assert result == [
        "sensor.comfoair_bridge_exhaust_air_temp",
        "sensor.comfoair_bridge_supply_air_temp",
    ]
