import json
from unittest.mock import patch
import pytest
import yaml

# Ensure app.py can import config_manager from parent dir
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app


@pytest.fixture
def config_file(tmp_path):
    cfg = {
        "bedrock": {"address": "0.0.0.0", "port": 19132},
        "remote": {"address": "mc.example.com", "port": 25565, "auth-type": "offline"},
    }
    path = tmp_path / "config.yml"
    path.write_text(yaml.dump(cfg))
    return str(path)


@pytest.fixture
def client(config_file):
    app = create_app(config_path=config_file)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestIndex:
    def test_renders_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Switch Bedrock Bridge" in resp.data

    def test_shows_current_address(self, client):
        resp = client.get("/")
        assert b"mc.example.com" in resp.data


class TestUpdateConfig:
    @patch("app.subprocess.run")
    def test_saves_and_restarts(self, mock_run, client, config_file):
        resp = client.post(
            "/api/config",
            data=json.dumps({"address": "new.server.com", "port": 25566, "auth_type": "online"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_run.assert_called_once_with(["pkill", "-f", "Geyser.jar"], check=False)

        # Verify config was actually written
        with open(config_file) as f:
            cfg = yaml.safe_load(f)
        assert cfg["remote"]["address"] == "new.server.com"
        assert cfg["remote"]["port"] == 25566

    def test_rejects_empty_address(self, client):
        resp = client.post(
            "/api/config",
            data=json.dumps({"address": "", "port": 25565}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "address" in resp.get_json()["error"]

    def test_rejects_invalid_port(self, client):
        resp = client.post(
            "/api/config",
            data=json.dumps({"address": "server.com", "port": 99999}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "Port" in resp.get_json()["error"]


class TestStatus:
    @patch("app.subprocess.run")
    def test_running(self, mock_run, client):
        mock_run.return_value.returncode = 0
        resp = client.get("/api/status")
        assert resp.get_json()["geyser_running"] is True

    @patch("app.subprocess.run")
    def test_not_running(self, mock_run, client):
        mock_run.return_value.returncode = 1
        resp = client.get("/api/status")
        assert resp.get_json()["geyser_running"] is False
