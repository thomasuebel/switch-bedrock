# Switch Bedrock Bridge

## What this is
A Docker service for CasaOS that lets a Nintendo Switch connect to any Minecraft Java server.
GeyserMC does the protocol translation; we provide a thin Docker wrapper + Flask web config UI.

## Architecture
```
Switch (UDP 19132) → GeyserMC (Bedrock↔Java) → Java Server (TCP 25565)
Browser (TCP 5000) → Flask Web UI → config.yml → pkill → GeyserMC restarts
```
- **GeyserMC Standalone** (single JAR) handles LAN discovery + protocol translation
- **Flask web UI** on port 5000 — 3 routes: `GET /`, `POST /api/config`, `GET /api/status`
- **entrypoint.sh** runs GeyserMC in a `while true` restart loop (background) + Flask (foreground)
- Config changes: Flask writes YAML, runs `pkill -f Geyser.jar`, loop auto-restarts GeyserMC

## Project structure
```
switch-bedrock/
├── CLAUDE.md                         # This file
├── README.md                         # User-facing setup guide
├── Dockerfile                        # eclipse-temurin:21-jre-alpine + python3 + flask
├── docker-compose.yml                # CasaOS-compatible, x-casaos metadata, network_mode: host
├── requirements.txt                  # Flask==3.1.0, PyYAML==6.0.2, pytest==8.3.4
├── .gitignore                        # .venv, __pycache__, .pytest_cache
├── docs/adr/001-architecture.md      # Architecture decision record
├── config/config.yml                 # Default GeyserMC config (ships in image as config-default/)
├── scripts/entrypoint.sh             # Downloads JAR, runs GeyserMC loop + Flask
└── web/
    ├── app.py                        # Flask app factory — create_app(config_path)
    ├── config_manager.py             # load_config, save_config, get/set_remote_server
    ├── templates/index.html          # Config form + connection instructions (dark theme)
    ├── static/style.css              # Dark theme CSS
    └── tests/
        ├── __init__.py
        ├── test_app.py               # 7 route tests (mocked subprocess)
        └── test_config_manager.py    # 12 YAML read/write/validation tests
```

## Key design decisions
- **App factory pattern**: `create_app(config_path)` so tests inject tmp_path configs
- **Config lives at `/app/config/config.yml`** inside container (Docker volume)
- **Default config copied from `/app/config-default/`** on first run only
- **GeyserMC JAR downloaded at runtime** (not baked into image) — stays current
- **auth-type: offline** by default (Switch players don't have Java accounts)
- **network_mode: host** in docker-compose.yml for LAN broadcast discovery to work

## Running tests
```bash
# Uses virtualenv at .venv/ — create with: python3 -m venv .venv && .venv/bin/pip install flask pyyaml pytest
cd web && ../.venv/bin/python -m pytest tests/ -v
```
19 tests total (12 config_manager + 7 app). All passing.

## Building & running
```bash
# With podman (no docker on this dev machine):
podman machine start
podman build -t switch-bedrock .
podman run -d --name switch-bedrock -p 19132:19132/udp -p 5001:5000/tcp switch-bedrock

# Or with docker compose (on CasaOS target):
docker compose up -d
```

## Dev environment notes
- macOS (darwin), Python 3.14.3 via Homebrew at `/opt/homebrew/bin/python3`
- **Always use a virtualenv** — `.venv/` in project root, never install globally
- No `docker` CLI available — use `podman` (at `/opt/homebrew/bin/podman`)
- Port 5000 is taken on macOS (AirPlay Receiver) — map to 5001 when testing locally
- Container verified working: GeyserMC 2.9.4 starts, Flask serves UI, `/api/status` returns `geyser_running: true`

## Container paths (inside Docker)
| Path | Purpose |
|------|---------|
| `/app/web/` | Flask app + templates + static |
| `/app/config/` | GeyserMC config.yml (Docker volume) |
| `/app/config-default/` | Shipped default config (copied on first run) |
| `/app/geyser/` | GeyserMC JAR + runtime data (Docker volume) |
| `/app/entrypoint.sh` | Container entrypoint |

## GeyserMC config keys we manage
- `remote.address` — Java server hostname/IP
- `remote.port` — Java server port (default 25565)
- `remote.auth-type` — `offline`, `online`, or `floodgate`

## What's NOT built yet
- No HTTPS / authentication on the web UI
- No GeyserMC version pinning (always downloads latest)
- No log viewer in the web UI
- No git repo initialized yet
