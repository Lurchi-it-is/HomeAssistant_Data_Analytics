from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from ha_data_analytics.azure_blob import AzureCsvRepository, EntitySeries
from ha_data_analytics.charts import build_chart, latest_kpi_value
from ha_data_analytics.config import load_config
from ha_data_analytics.dashboards import CHART_TYPES, Dashboard, DashboardStore, WidgetConfig
from ha_data_analytics.data import RESAMPLE_RULES, filter_and_resample, parse_homeassistant_csv
from ha_data_analytics.entity_selection import available_datetime_range, select_blobs_for_range

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

        entities = _load_entities_cached(
            config.connection_string,
            config.container_name,
            config.blob_prefix,
        )
        if not entities:
            st.warning("Keine CSV-Dateien im Storage Account gefunden.")
            st.stop()

        _dashboard_controls(store)
        start_at, end_at = _time_controls(entities)
        resample_label = st.selectbox("Resampling", list(RESAMPLE_RULES.keys()), index=0)
        aggregation_label = st.selectbox("Aggregation", list(AGGREGATIONS.keys()), index=0)

    dashboard: Dashboard = st.session_state.dashboard
    _widget_builder(entities, resample_label, aggregation_label)

    st.divider()
    if not dashboard.widgets:
        st.info("Fuege links oder oben ein Widget hinzu, um das Dashboard zu starten.")
        return

    entities_by_name = {entity.name: entity for entity in entities}
    for widget in list(dashboard.widgets):
        _render_widget(widget, entities_by_name, start_at, end_at)


def _init_state() -> None:
    if "dashboard" not in st.session_state:
        st.session_state.dashboard = Dashboard(name="Mein Dashboard")


@st.cache_data(show_spinner=False, ttl=300)
def _load_entities_cached(connection_string: str, container_name: str, prefix: str) -> list[EntitySeries]:
    return AzureCsvRepository(connection_string, container_name, prefix).list_entities()


@st.cache_data(show_spinner=False, ttl=300)
def _load_entity_data_cached(
    connection_string: str,
    container_name: str,
    prefix: str,
    entity_name: str,
    blob_names: tuple[str, ...],
) -> pd.DataFrame:
    repository = AzureCsvRepository(connection_string, container_name, prefix)
    frames = []
    for blob_name in blob_names:
        frame = parse_homeassistant_csv(repository.download_csv(blob_name), entity_name)
        frame["source_blob"] = blob_name
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)


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


def _time_controls(entities: list[EntitySeries]) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    st.header("Zeitraum")
    now = datetime.now().replace(second=0, microsecond=0)
    bounds = available_datetime_range(entities)
    if bounds is None:
        st.warning("Kein Monatsbereich aus Dateinamen ermittelbar.")
        data_start = pd.Timestamp(now.replace(day=1, hour=0, minute=0))
        data_end = pd.Timestamp(now)
    else:
        data_start, data_end = bounds
        st.caption(f"Verfuegbare Daten: {data_start:%d.%m.%Y %H:%M} bis {data_end:%d.%m.%Y %H:%M}")

    default_start = max(data_start, pd.Timestamp(data_end).replace(day=1, hour=0, minute=0))
    if default_start > data_end:
        default_start = data_start

    start_date = st.date_input(
        "Von Datum",
        value=default_start.date(),
        min_value=data_start.date(),
        max_value=data_end.date(),
    )
    start_time = st.time_input("Von Uhrzeit", value=default_start.time())
    end_date = st.date_input(
        "Bis Datum",
        value=data_end.date(),
        min_value=data_start.date(),
        max_value=data_end.date(),
    )
    end_time = st.time_input("Bis Uhrzeit", value=data_end.time())

    start = pd.Timestamp.combine(start_date, start_time)
    end = pd.Timestamp.combine(end_date, end_time)
    if start < data_start or end > data_end:
        st.error("Der gewaehlte Zeitraum liegt ausserhalb des verfuegbaren Datenbereichs.")
        st.stop()
    if end < start:
        st.error("Der Bis-Zeitpunkt muss nach dem Von-Zeitpunkt liegen.")
        st.stop()
    return start, end


def _widget_builder(
    entities: list[EntitySeries],
    resample_label: str,
    aggregation_label: str,
) -> None:
    st.subheader("Widget hinzufuegen")
    entity_options = [entity.name for entity in entities]
    search = st.text_input("Entity Suche", placeholder="z. B. comfoair, backup, temperature")
    if search:
        terms = [term.casefold() for term in search.split() if term.strip()]
        entity_options = [
            name for name in entity_options if all(term in name.casefold() for term in terms)
        ]

    selected_entities = st.multiselect(
        "Entities",
        options=entity_options,
        help="Mehrere Entities werden gemeinsam in einem Graph angezeigt.",
    )
    col_type, col_title, col_add = st.columns([1.4, 3, 0.8])

    chart_type = col_type.selectbox("Visualisierung", CHART_TYPES)
    default_title = f"{chart_type}: {', '.join(selected_entities[:3])}"
    if len(selected_entities) > 3:
        default_title += f" + {len(selected_entities) - 3} weitere"
    title = col_title.text_input("Titel", value=default_title)

    if col_add.button("Hinzufuegen", use_container_width=True, disabled=not selected_entities):
        st.session_state.dashboard.widgets.append(
            WidgetConfig(
                chart_type=chart_type,
                title=title,
                entity_names=selected_entities,
                aggregation=AGGREGATIONS[aggregation_label],
                resample_rule=RESAMPLE_RULES[resample_label],
            )
        )
        st.rerun()


def _render_widget(
    widget: WidgetConfig,
    entities_by_name: dict[str, EntitySeries],
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
            raw_df = _load_widget_data(config, entities_by_name, widget, start, end)
            df = filter_and_resample(raw_df, start, end, widget.resample_rule, widget.aggregation)
        except Exception as exc:
            st.error(f"Daten konnten nicht geladen werden: {exc}")
            return

        if df.empty:
            st.warning("Keine Daten fuer die aktuelle Auswahl.")
            return

        if widget.chart_type == "KPI":
            _render_kpis(df)
        elif widget.chart_type == "Tabelle":
            columns = [
                column
                for column in ["timestamp", "sensor", "state", "state_text", "state_numeric", "source_blob"]
                if column in df.columns
            ]
            st.dataframe(df[columns], use_container_width=True, hide_index=True)
        else:
            st.plotly_chart(build_chart(widget, df), use_container_width=True)

        with st.expander("Datenvorschau"):
            st.caption(f"{len(df)} Zeilen")
            st.dataframe(df.head(250), use_container_width=True, hide_index=True)


def _load_widget_data(
    config,
    entities_by_name: dict[str, EntitySeries],
    widget: WidgetConfig,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> pd.DataFrame:
    frames = []
    for entity_name in widget.entity_names:
        entity = entities_by_name.get(entity_name)
        if entity is None:
            continue
        blob_names = tuple(blob.blob_name for blob in select_blobs_for_range(entity, start, end))
        if not blob_names:
            continue
        frames.append(
            _load_entity_data_cached(
                config.connection_string,
                config.container_name,
                config.blob_prefix,
                entity_name,
                blob_names,
            )
        )

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "sensor"]).reset_index(drop=True)


def _render_kpis(df: pd.DataFrame) -> None:
    sensors = sorted(df["sensor"].dropna().unique())
    if not sensors:
        st.metric("Wert", latest_kpi_value(df))
        return
    columns = st.columns(min(len(sensors), 4))
    for index, sensor in enumerate(sensors):
        columns[index % len(columns)].metric(sensor, latest_kpi_value(df[df["sensor"] == sensor]))


if __name__ == "__main__":
    main()
