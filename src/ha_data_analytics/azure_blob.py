from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

from azure.storage.blob import BlobServiceClient


@dataclass(frozen=True)
class SensorBlob:
    name: str
    blob_name: str
    size: int | None = None
    month: str | None = None


@dataclass(frozen=True)
class EntitySeries:
    name: str
    blobs: tuple[SensorBlob, ...]


def sensor_name_from_blob(blob_name: str) -> str:
    path = PurePosixPath(blob_name)
    return path.stem


def entity_name_from_blob(blob_name: str) -> str:
    return re.sub(r"__\d{4}-\d{2}$", "", sensor_name_from_blob(blob_name))


def month_from_blob(blob_name: str) -> str | None:
    match = re.search(r"__(\d{4}-\d{2})$", sensor_name_from_blob(blob_name))
    if not match:
        return None
    return match.group(1)


class AzureCsvRepository:
    def __init__(self, connection_string: str, container_name: str, prefix: str = "") -> None:
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING ist nicht gesetzt.")
        if not container_name:
            raise ValueError("AZURE_STORAGE_CONTAINER ist nicht gesetzt.")

        self._container = BlobServiceClient.from_connection_string(
            connection_string
        ).get_container_client(container_name)
        self._prefix = prefix.strip("/")

    def list_sensors(self) -> list[SensorBlob]:
        blobs = self._container.list_blobs(name_starts_with=self._prefix or None)
        sensors: list[SensorBlob] = []
        for blob in blobs:
            if not blob.name.lower().endswith(".csv"):
                continue
            sensors.append(
                SensorBlob(
                    name=sensor_name_from_blob(blob.name),
                    blob_name=blob.name,
                    size=getattr(blob, "size", None),
                    month=month_from_blob(blob.name),
                )
            )
        return sorted(sensors, key=lambda sensor: sensor.name.casefold())

    def list_entities(self) -> list[EntitySeries]:
        grouped: dict[str, list[SensorBlob]] = {}
        for sensor in self.list_sensors():
            entity_name = entity_name_from_blob(sensor.blob_name)
            grouped.setdefault(entity_name, []).append(
                SensorBlob(
                    name=entity_name,
                    blob_name=sensor.blob_name,
                    size=sensor.size,
                    month=sensor.month,
                )
            )

        entities = [
            EntitySeries(
                name=name,
                blobs=tuple(
                    sorted(
                        blobs,
                        key=lambda blob: (
                            blob.month or "9999-99",
                            blob.blob_name.casefold(),
                        ),
                    )
                ),
            )
            for name, blobs in grouped.items()
        ]
        return sorted(entities, key=lambda entity: entity.name.casefold())

    def download_csv(self, blob_name: str) -> bytes:
        downloader = self._container.download_blob(blob_name)
        return downloader.readall()
