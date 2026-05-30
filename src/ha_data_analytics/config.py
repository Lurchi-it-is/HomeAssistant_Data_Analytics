from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    connection_string: str
    container_name: str
    blob_prefix: str
    dashboard_dir: Path


def load_config() -> AppConfig:
    load_dotenv()
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    container_name = os.getenv("AZURE_STORAGE_CONTAINER", "").strip()
    blob_prefix = os.getenv("AZURE_STORAGE_PREFIX", "").strip().strip("/")
    dashboard_dir = Path(os.getenv("HA_DASHBOARD_DIR", "app_data/dashboards"))

    return AppConfig(
        connection_string=connection_string,
        container_name=container_name,
        blob_prefix=blob_prefix,
        dashboard_dir=dashboard_dir,
    )
