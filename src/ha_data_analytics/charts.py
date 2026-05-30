from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ha_data_analytics.dashboards import WidgetConfig


def build_chart(widget: WidgetConfig, df: pd.DataFrame) -> go.Figure:
    chart_type = widget.chart_type
    title = widget.title or widget.sensor_name

    if chart_type == "Linie":
        return px.line(df, x="timestamp", y="state_numeric", title=title)
    if chart_type == "Flaeche":
        return px.area(df, x="timestamp", y="state_numeric", title=title)
    if chart_type == "Balken":
        return px.bar(df, x="timestamp", y="state_numeric", title=title)
    if chart_type == "Scatter":
        return px.scatter(df, x="timestamp", y="state_numeric", title=title)
    if chart_type == "Histogramm":
        return px.histogram(df, x="state_numeric", title=title)
    if chart_type == "Boxplot":
        return px.box(df, y="state_numeric", title=title)
    if chart_type == "Heatmap":
        return _heatmap(df, title)

    raise ValueError(f"Nicht unterstuetzter Chart-Typ: {chart_type}")


def latest_kpi_value(df: pd.DataFrame) -> str:
    if df.empty:
        return "Keine Daten"
    latest = df.sort_values("timestamp").iloc[-1]
    numeric = latest.get("state_numeric")
    if pd.notna(numeric):
        return f"{numeric:g}"
    return str(latest.get("state_text", ""))


def _heatmap(df: pd.DataFrame, title: str) -> go.Figure:
    heatmap_df = df.dropna(subset=["state_numeric"]).copy()
    if heatmap_df.empty:
        return go.Figure().update_layout(title=title)

    heatmap_df["datum"] = heatmap_df["timestamp"].dt.date.astype(str)
    heatmap_df["stunde"] = heatmap_df["timestamp"].dt.hour
    pivot = heatmap_df.pivot_table(
        index="stunde",
        columns="datum",
        values="state_numeric",
        aggfunc="mean",
    )
    figure = px.imshow(
        pivot,
        aspect="auto",
        title=title,
        labels={"x": "Datum", "y": "Stunde", "color": "Wert"},
    )
    return figure
