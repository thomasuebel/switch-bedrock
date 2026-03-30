# ADR 001: Architecture Decisions

## Status
Accepted

## Context
Nintendo Switch runs Minecraft Bedrock Edition and cannot connect to custom server IPs — only LAN games and featured servers. We need a way to bridge a Switch to any Java Edition server, running as a Docker service on CasaOS.

## Decisions

### Use GeyserMC Standalone
**Choice:** GeyserMC Standalone JAR, not a plugin.
**Rationale:** GeyserMC already handles LAN discovery (responds to broadcast pings on UDP 19132) and Bedrock↔Java protocol translation. No custom proxy code needed. Standalone mode requires no Spigot/Paper server.

### Restart loop instead of process manager
**Choice:** `while true; do java -jar Geyser.jar; sleep 1; done` in entrypoint.sh.
**Rationale:** When the user changes config via the web UI, Flask runs `pkill -f Geyser.jar`. The loop automatically restarts GeyserMC with the new config. No supervisord, no s6, no extra dependencies.

### Flask for the web UI
**Choice:** Flask with server-side rendering.
**Rationale:** Minimal dependency footprint. The UI is a single form — no need for a SPA framework. PyYAML reads/writes GeyserMC's config.yml directly.

### App factory pattern
**Choice:** `create_app(config_path)` factory in app.py.
**Rationale:** Allows tests to inject a temp config path. No global state.

### Offline auth by default
**Choice:** `auth-type: offline` in the default config.
**Rationale:** Switch players typically don't have Java accounts. Offline mode lets them connect immediately. Users can switch to `online` via the web UI if needed.

### CasaOS integration via x-casaos
**Choice:** `x-casaos` metadata in docker-compose.yml.
**Rationale:** CasaOS reads this to display the app in its dashboard with correct name, icon, category, and port mapping. No separate app manifest needed.

## Consequences
- The entire bridge is a single container with two processes (GeyserMC + Flask)
- Config changes require a GeyserMC restart (~3 seconds)
- No hot-reload of GeyserMC config (it doesn't support it)
