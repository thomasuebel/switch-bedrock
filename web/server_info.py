"""Query the configured Java server via Minecraft's Server List Ping.

Wraps mcstatus.JavaServer and caches the result for CACHE_TTL seconds so
the dashboard can refresh without hammering the upstream server.
"""

import time
from datetime import datetime, timezone

from mcstatus import JavaServer

CACHE_TTL = 60
LOOKUP_TIMEOUT = 3

_cache: dict[tuple[str, int], tuple[float, dict]] = {}


def clear_cache():
    _cache.clear()


def query(address, port, *, use_cache=True):
    key = (address, int(port))
    now = time.monotonic()
    cached = _cache.get(key)
    if use_cache and cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    result = _ping(address, int(port))
    _cache[key] = (now, result)
    return result


def _ping(address, port):
    base = {
        "address": address,
        "port": port,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        server = JavaServer.lookup(f"{address}:{port}", timeout=LOOKUP_TIMEOUT)
        status = server.status(tries=1)
    except Exception as e:
        # Any failure (DNS, timeout, refused, protocol) → render as offline.
        message = str(e) or type(e).__name__
        return {**base, "online": False, "error": message}

    sample = []
    if status.players.sample:
        sample = [p.name for p in status.players.sample]

    return {
        **base,
        "online": True,
        "motd": status.motd.to_plain(),
        "players": {
            "online": status.players.online,
            "max": status.players.max,
            "sample": sample,
        },
        "version": {
            "name": status.version.name,
            "protocol": status.version.protocol,
        },
        "latency_ms": round(status.latency, 1),
        "icon": status.icon,
    }
