from __future__ import annotations

from datetime import date, time

import pandas as pd
import streamlit as st

from ha_data_analytics.azure_blob import AzureCsvRepository, SensorBlob
from ha_data_analytics.charts import build_chart, latest_kpi_value
from ha_data_analytics.config import load_config
from ha_data_analytics.dashboards import CHART_TYPES, Dashboard, DashboardStore, WidgetConfig
from ha_data_analytics.data import RESAMPLE_RULES, filter_and_resample, parse_homeassistant_csv

AGGREGATIONS = {
    "Mittelwert": "mean",
    "Minimum": "min",
    "Maximum": "max",
    "Summe": "sum",
    "Anzahl": "count",
}


def main() -> None:
    st.set_page_config(page_title="Home Assistant Data Analytics", layout="wide")
    st.title("Home Assistant Data Analytics")

    config = load_config()
    store = DashboardStore(config.dashboard_dir)
    _init_state()

    with st.sidebar:
        st.header("Datenquelle")
        if not config.connection_string or not config.container_name:
            st.error("Azure-Konfiguration fehlt. Bitte `.env` aus `.env.example` erstellen.")
            st.stop()

        sensors = _load_sensors_cached(
            config.connection_string,
            config.container_name,
            config.blob_prefix,
        )
        if not sensors:
            st.warning("Keine CSV-Dateien im Storage Account gefunden.")
            st.stop()

        _dashboard_controls(store)
        start_date, end_date = _time_controls()
        resample_label = st.selectbox("Resampling", list(RESAMPLE_RULES.keys()), index=0)
        aggregation_label = st.selectbox("Aggregation", list(AGGREGATIONS.keys()), index=0)

    dashboard: Dashboard = st.session_state.dashboard
    _widget_builder(sensors, resample_label, aggregation_label)

    st.divider()
    if not dashboard.widgets:
        st.info("Fuege links oder oben ein Widget hinzu, um das Dashboard zu starten.")
        return

    for widget in list(dashboard.widgets):
        _render_widget(widget, start_date, end_date)


def _init_state() -> None:
    if "dashboard" not in st.session_state:
        st.session_state.dashboard = Dashboard(name="Mein Dashboard")


@st.cache_data(show_spinner=False, ttl=300)
def _load_sensors_cached(connection_string: str, container_name: str, prefix: str) -> list[SensorBlob]:
    return AzureCsvRepository(connection_string, container_name, prefix).list_sensors()


@st.cache_data(show_spinner=False, ttl=300)
def _load_csv_cached(
    connection_string: str,
    container_name: str,
    prefix: str,
    blob_name: str,
    sensor_name: str,
) -> pd.DataFrame:
    repository = AzureCsvRepository(connection_string, container_name, prefix)
    return parse_homeassistant_csv(repository.download_csv(blob_name), sensor_name)


def _dashboard_controls(store: DashboardStore) -> None:
    st.header("Dashboard")
    dashboard: Dashboard = st.session_state.dashboard
    dashboard.name = st.text_input("Name", value=dashboard.name)

    available = store.list_dashboards()
    selected = st.selectbox("Gespeicherte Dashboards", [""] + available, format_func=lambda item: item or "-")
    col_load, col_save, col_delete = st.columns(3)
    if col_load.button("Laden", use_container_width=True, disabled=not selected):
        st.session_state.dashboard = store.load(selected)
        st.rerun()
    if col_save.button("Speichern", use_container_width=True):
        store.save(st.session_state.dashboard)
        st.success("Dashboard gespeichert.")
    if col_delete.button("Loeschen", use_container_width=True, disabled=not selected):
        store.delete(selected)
        st.success("Dashboard geloescht.")
        st.rerun()


def _time_controls() -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    st.header("Zeitraum")
    use_filter = st.checkbox("Zeitraum begrenzen", value=False)
    if not use_filter:
        return None, None

    start = st.date_input("Start", value=date.today())
    end = st.date_input("Ende", value=date.today())
    return pd.Timestamp.combine(start, time.min), pd.Timestamp.combine(end, time.max)


def _widget_builder(
    sensors: list[SensorBlob],
    resample_label: str,
    aggregation_label: str,
) -> None:
    st.subheader("Widget hinzufuegen")
    sensor_options = {sensor.name: sensor for sensor in sensors}
    col_sensor, col_type, col_title, col_add = st.columns([2, 1.4, 2, 0.8])

    sensor_name = col_sensor.selectbox("Sensor", list(sensor_options.keys()))
    chart_type = col_type.selectbox("Visualisierung", CHART_TYPES)
    title = col_title.text_input("Titel", value=f"{chart_type}: {sensor_name}")

    if col_add.button("Hinzufuegen", use_container_width=True):
        sensor = sensor_options[sensor_name]
        st.session_state.dashboard.widgets.append(
            WidgetConfig(
                sensor_blob=sensor.blob_name,
                sensor_name=sensor.name,
                chart_type=chart_type,
                title=title,
                aggregation=AGGREGATIONS[aggregation_label],
                resample_rule=RESAMPLE_RULES[resample_label],
            )
        )
        st.rerun()


def _render_widget(
    widget: WidgetConfig,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> None:
    config = load_config()
    with st.container(border=True):
        col_title, col_remove = st.columns([5, 1])
        col_title.subheader(widget.title)
        if col_remove.button("Entfernen", key=f"remove-{widget.widget_id}", use_container_width=True):
            st.session_state.dashboard.widgets = [
                item for item in st.session_state.dashboard.widgets if item.widget_id != widget.widget_id
            ]
            st.rerun()

        try:
            raw_df = _load_csv_cached(
                config.connection_string,
                config.container_name,
                config.blob_prefix,
                widget.sensor_blob,
                widget.sensor_name,
            )
            df = filter_and_resample(raw_df, start, end, widget.resample_rule, widget.aggregation)
        except Exception as exc:
            st.error(f"Daten konnten nicht geladen werden: {exc}")
            return

        if df.empty:
            st.warning("Keine Daten fuer die aktuelle Auswahl.")
            return

        if widget.chart_type == "KPI":
            st.metric(widget.sensor_name, latest_kpi_value(df))
        elif widget.chart_type == "Tabelle":
            columns = [column for column in ["timestamp", "sensor", "state", "state_text", "state_numeric"] if column in df.columns]
            st.dataframe(df[columns], use_container_width=True, hide_index=True)
        else:
            st.plotly_chart(build_chart(widget, df), use_container_width=True)

        with st.expander("Datenvorschau"):
            st.caption(f"{len(df)} Zeilen")
            st.dataframe(df.head(250), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
