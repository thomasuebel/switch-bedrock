"""Check and update GeyserMC / Floodgate versions.

Sources are declared in sources.yml. For each project we:
  - read the locally installed build from a sidecar JSON next to the JAR
  - fetch the latest build metadata over HTTPS (cached for CACHE_TTL seconds)
  - optionally download + atomic-swap the JAR if the project is installable
"""

import json
import os
import time
import urllib.request
from pathlib import Path

import yaml

CACHE_TTL = 3600
USER_AGENT = "switch-bedrock-bridge/1.0"
DEFAULT_SOURCES_PATH = os.path.join(os.path.dirname(__file__), "sources.yml")

_latest_cache: dict[str, tuple[float, dict]] = {}


class UpdateError(Exception):
    pass


def load_sources(path=DEFAULT_SOURCES_PATH):
    with open(path) as f:
        return yaml.safe_load(f)


def _sidecar_path(jar_path):
    return jar_path + ".meta.json"


def read_local(jar_path):
    """Return the build metadata for the installed JAR, or None if unknown."""
    if not os.path.exists(jar_path):
        return None
    sidecar = _sidecar_path(jar_path)
    if not os.path.exists(sidecar):
        return {"build": None, "version": None}
    try:
        with open(sidecar) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"build": None, "version": None}


def fetch_latest(metadata_url, *, use_cache=True):
    """Fetch the latest build metadata from the project's build API."""
    now = time.monotonic()
    cached = _latest_cache.get(metadata_url)
    if use_cache and cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    req = urllib.request.Request(metadata_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise UpdateError(f"Could not fetch {metadata_url}: {e}") from e

    _latest_cache[metadata_url] = (now, data)
    return data


def clear_cache():
    _latest_cache.clear()


def get_status(sources=None):
    """Return per-project version status for the dashboard."""
    if sources is None:
        sources = load_sources()
    result = {}
    for name, cfg in sources.items():
        local = read_local(cfg["jar_path"]) if cfg.get("installable") else None
        try:
            latest = fetch_latest(cfg["metadata_url"])
            latest_summary = {"build": latest.get("build"), "version": latest.get("version")}
            error = None
        except UpdateError as e:
            latest_summary = None
            error = str(e)

        update_available = False
        if cfg.get("installable") and latest_summary and local is not None:
            local_build = local.get("build")
            if local_build is None or (latest_summary["build"] and latest_summary["build"] > local_build):
                update_available = True

        result[name] = {
            "installable": bool(cfg.get("installable")),
            "local": local,
            "latest": latest_summary,
            "update_available": update_available,
            "project_url": cfg.get("project_url"),
            "error": error,
        }
    return result


def download(project, sources=None):
    """Download the latest JAR for *project* and atomically swap it in.

    Returns the new metadata dict. Raises UpdateError on failure.
    """
    if sources is None:
        sources = load_sources()
    if project not in sources:
        raise UpdateError(f"Unknown project: {project}")
    cfg = sources[project]
    if not cfg.get("installable"):
        raise UpdateError(f"{project} is not installable from this dashboard")

    latest = fetch_latest(cfg["metadata_url"], use_cache=False)
    jar_path = Path(cfg["jar_path"])
    jar_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = jar_path.with_suffix(jar_path.suffix + ".new")

    req = urllib.request.Request(cfg["download_url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_path, "wb") as out:
            while chunk := resp.read(65536):
                out.write(chunk)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise UpdateError(f"Download failed: {e}") from e

    os.replace(tmp_path, jar_path)
    with open(_sidecar_path(str(jar_path)), "w") as f:
        json.dump(latest, f)
    return latest
