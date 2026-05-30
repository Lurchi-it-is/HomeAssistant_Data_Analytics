from __future__ import annotations

from types import SimpleNamespace

from ha_data_analytics.azure_blob import (
    AzureCsvRepository,
    entity_name_from_blob,
    month_from_blob,
    sensor_name_from_blob,
)


def test_sensor_name_from_blob_uses_file_stem() -> None:
    assert sensor_name_from_blob("exports/sensor.energy.csv") == "sensor.energy"


def test_entity_name_from_blob_removes_month_suffix() -> None:
    assert entity_name_from_blob("exports/sensor.energy__2026-05.csv") == "sensor.energy"
    assert month_from_blob("exports/sensor.energy__2026-05.csv") == "2026-05"


def test_list_sensors_filters_csv_and_uses_prefix(monkeypatch) -> None:
    calls = {}

    class FakeContainer:
        def list_blobs(self, name_starts_with=None):
            calls["prefix"] = name_starts_with
            return [
                SimpleNamespace(name="exports/sensor.energy.csv", size=10),
                SimpleNamespace(name="exports/readme.txt", size=5),
                SimpleNamespace(name="exports/binary.door.CSV", size=8),
            ]

        def download_blob(self, blob_name):
            raise AssertionError("download_blob should not be called")

    class FakeBlobServiceClient:
        @classmethod
        def from_connection_string(cls, connection_string):
            calls["connection_string"] = connection_string
            return cls()

        def get_container_client(self, container_name):
            calls["container_name"] = container_name
            return FakeContainer()

    monkeypatch.setattr(
        "ha_data_analytics.azure_blob.BlobServiceClient",
        FakeBlobServiceClient,
    )

    repository = AzureCsvRepository("UseDevelopmentStorage=true", "ha", "exports")
    sensors = repository.list_sensors()

    assert calls == {
        "connection_string": "UseDevelopmentStorage=true",
        "container_name": "ha",
        "prefix": "exports",
    }
    assert [sensor.name for sensor in sensors] == ["binary.door", "sensor.energy"]


def test_download_csv_reads_blob(monkeypatch) -> None:
    class FakeDownloader:
        def readall(self):
            return b"timestamp_local,state\n2026-05-01 06:00:00,1\n"

    class FakeContainer:
        def list_blobs(self, name_starts_with=None):
            return []

        def download_blob(self, blob_name):
            assert blob_name == "sensor.csv"
            return FakeDownloader()

    class FakeBlobServiceClient:
        @classmethod
        def from_connection_string(cls, connection_string):
            return cls()

        def get_container_client(self, container_name):
            return FakeContainer()

    monkeypatch.setattr(
        "ha_data_analytics.azure_blob.BlobServiceClient",
        FakeBlobServiceClient,
    )

    repository = AzureCsvRepository("UseDevelopmentStorage=true", "ha")

    assert repository.download_csv("sensor.csv").startswith(b"timestamp_local")


def test_list_entities_groups_monthly_csv_files(monkeypatch) -> None:
    class FakeContainer:
        def list_blobs(self, name_starts_with=None):
            return [
                SimpleNamespace(name="exports/sensor.energy__2026-04.csv", size=10),
                SimpleNamespace(name="exports/sensor.energy__2026-05.csv", size=10),
                SimpleNamespace(name="exports/sensor.power__2026-05.csv", size=10),
            ]

        def download_blob(self, blob_name):
            raise AssertionError("download_blob should not be called")

    class FakeBlobServiceClient:
        @classmethod
        def from_connection_string(cls, connection_string):
            return cls()

        def get_container_client(self, container_name):
            return FakeContainer()

    monkeypatch.setattr(
        "ha_data_analytics.azure_blob.BlobServiceClient",
        FakeBlobServiceClient,
    )

    entities = AzureCsvRepository("UseDevelopmentStorage=true", "ha", "exports").list_entities()

    assert [entity.name for entity in entities] == ["sensor.energy", "sensor.power"]
    assert [blob.month for blob in entities[0].blobs] == ["2026-04", "2026-05"]
