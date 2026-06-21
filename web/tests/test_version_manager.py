import io
import json
import os
import sys
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import version_manager


@pytest.fixture(autouse=True)
def clear_cache():
    version_manager.clear_cache()
    yield
    version_manager.clear_cache()


@pytest.fixture
def jar(tmp_path):
    path = tmp_path / "Geyser.jar"
    path.write_bytes(b"jar-bytes")
    return str(path)


@pytest.fixture
def sources_file(tmp_path):
    path = tmp_path / "sources.yml"
    path.write_text(yaml.dump({
        "geyser": {
            "metadata_url": "https://example.test/geyser/meta",
            "download_url": "https://example.test/geyser/dl",
            "jar_path": str(tmp_path / "Geyser.jar"),
            "installable": True,
        },
        "floodgate": {
            "metadata_url": "https://example.test/floodgate/meta",
            "project_url": "https://example.test/floodgate",
            "installable": False,
        },
    }))
    return str(path)


def _fake_response(payload):
    return io.BytesIO(json.dumps(payload).encode())


class TestReadLocal:
    def test_returns_none_when_jar_missing(self, tmp_path):
        assert version_manager.read_local(str(tmp_path / "nope.jar")) is None

    def test_returns_placeholder_when_sidecar_missing(self, jar):
        result = version_manager.read_local(jar)
        assert result == {"build": None, "version": None}

    def test_reads_sidecar(self, jar):
        with open(jar + ".meta.json", "w") as f:
            json.dump({"build": 42, "version": "2.9.4"}, f)
        result = version_manager.read_local(jar)
        assert result["build"] == 42
        assert result["version"] == "2.9.4"

    def test_handles_corrupt_sidecar(self, jar):
        with open(jar + ".meta.json", "w") as f:
            f.write("not json")
        assert version_manager.read_local(jar) == {"build": None, "version": None}


class TestFetchLatest:
    def test_fetches_and_caches(self):
        payload = {"build": 100, "version": "2.9.5"}
        with patch("version_manager.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value = _fake_response(payload)
            first = version_manager.fetch_latest("https://example.test/meta")
            second = version_manager.fetch_latest("https://example.test/meta")
        assert first == payload
        assert second == payload
        assert mock_open.call_count == 1

    def test_bypasses_cache_when_requested(self):
        payload = {"build": 100, "version": "2.9.5"}
        with patch("version_manager.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value = _fake_response(payload)
            version_manager.fetch_latest("https://example.test/meta")
            mock_open.return_value.__enter__.return_value = _fake_response(payload)
            version_manager.fetch_latest("https://example.test/meta", use_cache=False)
        assert mock_open.call_count == 2

    def test_raises_on_network_error(self):
        import urllib.error
        with patch("version_manager.urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            with pytest.raises(version_manager.UpdateError):
                version_manager.fetch_latest("https://example.test/meta")


class TestGetStatus:
    def test_reports_update_available(self, sources_file, jar):
        with open(jar + ".meta.json", "w") as f:
            json.dump({"build": 50, "version": "2.9.3"}, f)
        responses = {
            "https://example.test/geyser/meta": {"build": 100, "version": "2.9.5"},
            "https://example.test/floodgate/meta": {"build": 80, "version": "2.2.4"},
        }
        with patch("version_manager.fetch_latest", side_effect=lambda url: responses[url]):
            status = version_manager.get_status(version_manager.load_sources(sources_file))

        assert status["geyser"]["installable"] is True
        assert status["geyser"]["update_available"] is True
        assert status["geyser"]["local"]["build"] == 50
        assert status["geyser"]["latest"]["build"] == 100
        assert status["floodgate"]["installable"] is False
        assert status["floodgate"]["update_available"] is False
        assert status["floodgate"]["project_url"] == "https://example.test/floodgate"

    def test_no_update_when_up_to_date(self, sources_file, jar):
        with open(jar + ".meta.json", "w") as f:
            json.dump({"build": 100, "version": "2.9.5"}, f)
        with patch("version_manager.fetch_latest") as mock_fetch:
            mock_fetch.return_value = {"build": 100, "version": "2.9.5"}
            status = version_manager.get_status(version_manager.load_sources(sources_file))
        assert status["geyser"]["update_available"] is False

    def test_unknown_local_counts_as_update(self, sources_file, jar):
        # JAR exists but no sidecar — treat as needing refresh
        with patch("version_manager.fetch_latest") as mock_fetch:
            mock_fetch.return_value = {"build": 100, "version": "2.9.5"}
            status = version_manager.get_status(version_manager.load_sources(sources_file))
        assert status["geyser"]["update_available"] is True

    def test_records_fetch_error(self, sources_file):
        with patch("version_manager.fetch_latest", side_effect=version_manager.UpdateError("nope")):
            status = version_manager.get_status(version_manager.load_sources(sources_file))
        assert status["geyser"]["latest"] is None
        assert "nope" in status["geyser"]["error"]


class TestDownload:
    def test_atomic_swap_and_sidecar(self, sources_file, tmp_path):
        meta = {"build": 200, "version": "2.9.6"}
        with patch("version_manager.fetch_latest", return_value=meta), \
             patch("version_manager.urllib.request.urlopen") as mock_dl:
            mock_dl.return_value.__enter__.return_value = io.BytesIO(b"NEW-JAR-CONTENT")
            result = version_manager.download("geyser", version_manager.load_sources(sources_file))

        jar = tmp_path / "Geyser.jar"
        assert jar.read_bytes() == b"NEW-JAR-CONTENT"
        sidecar = json.loads((tmp_path / "Geyser.jar.meta.json").read_text())
        assert sidecar["build"] == 200
        assert result == meta
        # tmp file cleaned up
        assert not (tmp_path / "Geyser.jar.new").exists()

    def test_rejects_non_installable(self, sources_file):
        with pytest.raises(version_manager.UpdateError):
            version_manager.download("floodgate", version_manager.load_sources(sources_file))

    def test_rejects_unknown_project(self, sources_file):
        with pytest.raises(version_manager.UpdateError):
            version_manager.download("nope", version_manager.load_sources(sources_file))

    def test_leaves_jar_untouched_on_download_error(self, sources_file, tmp_path):
        jar = tmp_path / "Geyser.jar"
        jar.write_bytes(b"OLD")
        import urllib.error
        with patch("version_manager.fetch_latest", return_value={"build": 200, "version": "2.9.6"}), \
             patch("version_manager.urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            with pytest.raises(version_manager.UpdateError):
                version_manager.download("geyser", version_manager.load_sources(sources_file))
        assert jar.read_bytes() == b"OLD"
        assert not (tmp_path / "Geyser.jar.new").exists()
