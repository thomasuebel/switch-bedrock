import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server_info


@pytest.fixture(autouse=True)
def clear_cache():
    server_info.clear_cache()
    yield
    server_info.clear_cache()


def _fake_status(*, motd="A Minecraft Server", online=2, max_=20, sample=None,
                 version_name="1.21.4", protocol=769, latency=42.7, icon=None):
    sample_objs = [SimpleNamespace(name=n) for n in (sample or [])]
    return SimpleNamespace(
        motd=SimpleNamespace(to_plain=lambda: motd),
        players=SimpleNamespace(online=online, max=max_, sample=sample_objs or None),
        version=SimpleNamespace(name=version_name, protocol=protocol),
        latency=latency,
        icon=icon,
    )


class TestQueryOnline:
    def test_returns_normalized_payload(self):
        fake_status = _fake_status(sample=["alice", "bob"], icon="data:image/png;base64,xxx")
        server = MagicMock()
        server.status.return_value = fake_status
        with patch("server_info.JavaServer.lookup", return_value=server):
            info = server_info.query("mc.example.com", 25565)

        assert info["online"] is True
        assert info["address"] == "mc.example.com"
        assert info["port"] == 25565
        assert info["motd"] == "A Minecraft Server"
        assert info["players"] == {"online": 2, "max": 20, "sample": ["alice", "bob"]}
        assert info["version"] == {"name": "1.21.4", "protocol": 769}
        assert info["latency_ms"] == 42.7
        assert info["icon"] == "data:image/png;base64,xxx"
        assert "checked_at" in info

    def test_handles_empty_sample(self):
        server = MagicMock()
        server.status.return_value = _fake_status(sample=None)
        with patch("server_info.JavaServer.lookup", return_value=server):
            info = server_info.query("mc.example.com", 25565)
        assert info["players"]["sample"] == []


class TestQueryOffline:
    def test_returns_offline_on_exception(self):
        with patch("server_info.JavaServer.lookup", side_effect=ConnectionRefusedError("nope")):
            info = server_info.query("dead.example.com", 25565)
        assert info["online"] is False
        assert "nope" in info["error"]
        assert info["address"] == "dead.example.com"
        assert info["port"] == 25565

    def test_falls_back_to_type_name_when_message_empty(self):
        with patch("server_info.JavaServer.lookup", side_effect=TimeoutError()):
            info = server_info.query("slow.example.com", 25565)
        assert info["online"] is False
        assert info["error"] == "TimeoutError"


class TestCache:
    def test_returns_cached_within_ttl(self):
        server = MagicMock()
        server.status.return_value = _fake_status()
        with patch("server_info.JavaServer.lookup", return_value=server) as mock_lookup:
            server_info.query("host", 25565)
            server_info.query("host", 25565)
        assert mock_lookup.call_count == 1

    def test_bypasses_cache_when_requested(self):
        server = MagicMock()
        server.status.return_value = _fake_status()
        with patch("server_info.JavaServer.lookup", return_value=server) as mock_lookup:
            server_info.query("host", 25565)
            server_info.query("host", 25565, use_cache=False)
        assert mock_lookup.call_count == 2

    def test_separate_keys_for_different_servers(self):
        server = MagicMock()
        server.status.return_value = _fake_status()
        with patch("server_info.JavaServer.lookup", return_value=server) as mock_lookup:
            server_info.query("a", 25565)
            server_info.query("b", 25565)
        assert mock_lookup.call_count == 2

    def test_clear_cache_forces_refresh(self):
        server = MagicMock()
        server.status.return_value = _fake_status()
        with patch("server_info.JavaServer.lookup", return_value=server) as mock_lookup:
            server_info.query("host", 25565)
            server_info.clear_cache()
            server_info.query("host", 25565)
        assert mock_lookup.call_count == 2
