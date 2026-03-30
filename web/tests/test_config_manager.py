import pytest
import yaml
from config_manager import load_config, save_config, get_remote_server, set_remote_server


@pytest.fixture
def config_file(tmp_path):
    """Create a minimal config file and return its path."""
    cfg = {
        "bedrock": {"address": "0.0.0.0", "port": 19132},
        "remote": {"address": "mc.example.com", "port": 25565, "auth-type": "offline"},
    }
    path = tmp_path / "config.yml"
    path.write_text(yaml.dump(cfg))
    return str(path)


class TestLoadConfig:
    def test_returns_dict(self, config_file):
        cfg = load_config(config_file)
        assert isinstance(cfg, dict)
        assert cfg["remote"]["address"] == "mc.example.com"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nonexistent.yml"))


class TestSaveConfig:
    def test_round_trip(self, config_file):
        cfg = load_config(config_file)
        cfg["remote"]["address"] = "new.server.com"
        save_config(config_file, cfg)
        reloaded = load_config(config_file)
        assert reloaded["remote"]["address"] == "new.server.com"


class TestGetRemoteServer:
    def test_returns_flat_dict(self, config_file):
        result = get_remote_server(config_file)
        assert result == {
            "address": "mc.example.com",
            "port": 25565,
            "auth_type": "offline",
        }

    def test_defaults_when_remote_missing(self, tmp_path):
        path = tmp_path / "empty.yml"
        path.write_text(yaml.dump({"bedrock": {}}))
        result = get_remote_server(str(path))
        assert result["address"] == "127.0.0.1"
        assert result["port"] == 25565
        assert result["auth_type"] == "offline"


class TestSetRemoteServer:
    def test_updates_config(self, config_file):
        set_remote_server(config_file, "play.server.net", 25566, "online")
        result = get_remote_server(config_file)
        assert result == {
            "address": "play.server.net",
            "port": 25566,
            "auth_type": "online",
        }

    def test_strips_whitespace(self, config_file):
        set_remote_server(config_file, "  spaced.server.com  ", 25565)
        result = get_remote_server(config_file)
        assert result["address"] == "spaced.server.com"

    def test_empty_address_raises(self, config_file):
        with pytest.raises(ValueError, match="address"):
            set_remote_server(config_file, "  ", 25565)

    def test_invalid_port_raises(self, config_file):
        with pytest.raises(ValueError, match="Port"):
            set_remote_server(config_file, "server.com", 0)

    def test_port_too_high_raises(self, config_file):
        with pytest.raises(ValueError, match="Port"):
            set_remote_server(config_file, "server.com", 70000)

    def test_invalid_auth_type_raises(self, config_file):
        with pytest.raises(ValueError, match="auth_type"):
            set_remote_server(config_file, "server.com", 25565, "bogus")

    def test_port_as_string(self, config_file):
        set_remote_server(config_file, "server.com", "25565")
        result = get_remote_server(config_file)
        assert result["port"] == 25565
