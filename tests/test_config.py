from __future__ import annotations

from ha_data_analytics.config import load_config


def test_load_config_prefers_project_dotenv_over_existing_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "old-connection")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "old-container")
    monkeypatch.setenv("AZURE_STORAGE_PREFIX", "old-prefix")
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "AZURE_STORAGE_CONNECTION_STRING=new-connection",
                "AZURE_STORAGE_CONTAINER=backups",
                "AZURE_STORAGE_PREFIX=HomeAssistant/current/export",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config()

    assert config.connection_string == "new-connection"
    assert config.container_name == "backups"
    assert config.blob_prefix == "HomeAssistant/current/export"
