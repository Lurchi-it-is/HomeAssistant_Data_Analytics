from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


CHART_TYPES = (
    "KPI",
    "Tabelle",
    "Linie",
    "Flaeche",
    "Balken",
    "Scatter",
    "Histogramm",
    "Boxplot",
    "Heatmap",
)


@dataclass
class WidgetConfig:
    chart_type: str
    title: str
    entity_names: list[str] = field(default_factory=list)
    aggregation: str = "mean"
    resample_rule: str | None = None
    sensor_blob: str | None = None
    sensor_name: str = ""
    widget_id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if not self.entity_names and self.sensor_name:
            self.entity_names = [re.sub(r"__\d{4}-\d{2}$", "", self.sensor_name)]


@dataclass
class Dashboard:
    name: str
    widgets: list[WidgetConfig] = field(default_factory=list)
    version: int = 1
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DashboardStore:
    def __init__(self, dashboard_dir: Path) -> None:
        self.dashboard_dir = dashboard_dir
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)

    def list_dashboards(self) -> list[str]:
        return sorted(path.stem for path in self.dashboard_dir.glob("*.json"))

    def load(self, name: str) -> Dashboard:
        path = self._path_for(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Dashboard(
            name=payload["name"],
            version=int(payload.get("version", 1)),
            updated_at=payload.get("updated_at", ""),
            widgets=[WidgetConfig(**widget) for widget in payload.get("widgets", [])],
        )

    def save(self, dashboard: Dashboard) -> Path:
        dashboard.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._path_for(dashboard.name)
        path.write_text(json.dumps(asdict(dashboard), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def delete(self, name: str) -> None:
        path = self._path_for(name)
        if path.exists():
            path.unlink()

    def _path_for(self, name: str) -> Path:
        slug = slugify(name)
        if not slug:
            raise ValueError("Dashboard-Name darf nicht leer sein.")
        return self.dashboard_dir / f"{slug}.json"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return slug[:80]
