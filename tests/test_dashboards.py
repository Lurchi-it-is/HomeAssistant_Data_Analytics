from __future__ import annotations

from ha_data_analytics.dashboards import Dashboard, DashboardStore, WidgetConfig, slugify


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


def test_dashboard_store_delete(tmp_path) -> None:
    store = DashboardStore(tmp_path)
    store.save(Dashboard(name="Test"))

    store.delete("test")

    assert store.list_dashboards() == []


def test_slugify_limits_names_to_file_safe_values() -> None:
    assert slugify("  Mein Dashboard! 2026  ") == "mein-dashboard-2026"
