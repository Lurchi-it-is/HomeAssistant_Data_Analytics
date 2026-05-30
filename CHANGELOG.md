# Changelog

## 0.1.6 - 2026-05-30

- Added a per-widget value mode for cumulative total sensors that calculates period deltas such as daily usage.
- Added per-widget interval selection so existing charts can change the aggregation or total-delta period.

## 0.1.5 - 2026-05-30

- Added per-widget Entity search and multi-select editing so existing charts can add or remove Entities.

## 0.1.4 - 2026-05-30

- Added per-widget visualization selection so chart type can be changed directly inside an existing diagram.

## 0.1.3 - 2026-05-30

- Limited the Von/Bis date picker to the available data range derived from monthly CSV filenames.

## 0.1.2 - 2026-05-30

- Added Entity grouping across monthly CSV files such as `sensor.name__2026-05.csv`.
- Added Von/Bis datetime filtering that selects all matching monthly files before loading data.
- Added Entity search and multi-Entity widgets for shared graph visualizations.

## 0.1.1 - 2026-05-30

- Changed configuration loading so values from the project `.env` file override already-set shell environment variables.

## 0.1.0 - 2026-05-30

- Initial Streamlit dashboard builder for Home Assistant CSV files in Azure Blob Storage.
- Added CSV parsing, sensor selection by blob filename, time filtering, resampling, Plotly chart widgets, and local dashboard JSON persistence.
