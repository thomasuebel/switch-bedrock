"""Read and write GeyserMC config.yml."""

import yaml

DEFAULT_CONFIG_PATH = "/app/config/config.yml"


def load_config(path=DEFAULT_CONFIG_PATH):
    """Load the YAML config and return it as a dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def save_config(path, data):
    """Write *data* dict back to YAML."""
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_remote_server(path=DEFAULT_CONFIG_PATH):
    """Return the remote server settings as a flat dict."""
    cfg = load_config(path)
    remote = cfg.get("remote", {})
    return {
        "address": remote.get("address", "127.0.0.1"),
        "port": remote.get("port", 25565),
        "auth_type": remote.get("auth-type", "offline"),
    }


def set_remote_server(path, address, port, auth_type="offline"):
    """Validate and persist remote server settings."""
    address = address.strip()
    if not address:
        raise ValueError("Server address must not be empty")

    port = int(port)
    if not (1 <= port <= 65535):
        raise ValueError("Port must be between 1 and 65535")

    if auth_type not in ("offline", "online", "floodgate"):
        raise ValueError("auth_type must be offline, online, or floodgate")

    cfg = load_config(path)
    cfg.setdefault("remote", {})
    cfg["remote"]["address"] = address
    cfg["remote"]["port"] = port
    cfg["remote"]["auth-type"] = auth_type
    save_config(path, cfg)
