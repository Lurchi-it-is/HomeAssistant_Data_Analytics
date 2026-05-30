# HomeAssistant Data Analytics

Streamlit-Webtool zur Visualisierung von Home-Assistant CSV-Daten aus Azure Blob Storage.

## Funktionen

- CSV-Dateien direkt aus einem Azure Storage Container lesen.
- Monatsdateien automatisch zu Entities gruppieren, z. B. `sensor.energy__2026-05.csv` zu `sensor.energy`.
- Entities ueber Suche finden und mehrere Entities in einem Graph anzeigen.
- Home-Assistant Spalten wie `timestamp_utc`, `timestamp_local`, `state`, `changed_utc` und `updated_utc` parsen.
- Von/Bis-Zeitraum inklusive Uhrzeit filtern; auswaehlbare Datumswerte werden auf den vorhandenen Monatsbereich begrenzt.
- Dashboard Builder mit KPI, Tabelle, Linie, Flaeche, Balken, Scatter, Histogramm, Boxplot und Heatmap.
- Dashboards lokal als JSON speichern, laden und loeschen.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
Copy-Item .env.example .env
```

Danach `.env` mit dem Azure Storage Connection String und Container anpassen.

## Konfiguration

| Variable | Pflicht | Beschreibung |
| --- | --- | --- |
| `AZURE_STORAGE_CONNECTION_STRING` | Ja | Azure Storage Connection String mit Leserechten fuer den Container. |
| `AZURE_STORAGE_CONTAINER` | Ja | Name des Containers mit den CSV-Dateien. |
| `AZURE_STORAGE_PREFIX` | Nein | Optionaler Prefix/Ordner innerhalb des Containers. |
| `HA_DASHBOARD_DIR` | Nein | Lokaler Ordner fuer Dashboard JSON-Dateien. Default: `app_data/dashboards`. |

## Start

```powershell
streamlit run src/ha_data_analytics/app.py
```

## Tests

```powershell
pytest
```
