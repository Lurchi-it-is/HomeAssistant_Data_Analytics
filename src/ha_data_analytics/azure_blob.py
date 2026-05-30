from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from azure.storage.blob import BlobServiceClient


@dataclass(frozen=True)
class SensorBlob:
    name: str
    blob_name: str
    size: int | None = None


def sensor_name_from_blob(blob_name: str) -> str:
    path = PurePosixPath(blob_name)
    return path.stem


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
                )
            )
        return sorted(sensors, key=lambda sensor: sensor.name.casefold())

    def download_csv(self, blob_name: str) -> bytes:
        downloader = self._container.download_blob(blob_name)
        return downloader.readall()
