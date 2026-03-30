# Switch Bedrock Bridge for CasaOS

Connect your Nintendo Switch to any Minecraft Java Edition server — no mods, no hacks.

## How it works

Nintendo Switch can only join LAN games or featured servers. This service runs [GeyserMC](https://geysermc.org/) in a Docker container that:

1. **Advertises itself as a LAN game** — your Switch auto-discovers it
2. **Translates Bedrock protocol to Java** — connects to any Java Edition server
3. **Provides a web UI** — configure the target server from your browser

## Quick Start

### CasaOS

Import the `docker-compose.yml` via the CasaOS app installer.

### Docker Compose

```bash
git clone <this-repo> switch-bedrock
cd switch-bedrock
docker compose up -d
```

### Configuration

1. Open `http://<your-casaos-ip>:5000` in a browser
2. Enter your Java server's address and port
3. Click **Save & Restart**
4. On your Switch: Play → Friends → join the LAN game that appears

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 19132 | UDP | Bedrock/LAN discovery (Switch connects here) |
| 5000 | TCP | Web configuration UI |

## Authentication

By default, `auth-type` is set to `offline` so your Switch can connect without a Java account. Set it to `online` if the target server requires authentication (you'll need to link a Java account via the Geyser process).

## Requirements

- Docker & Docker Compose
- The Switch and the Docker host must be on the same LAN
- UDP port 19132 must not be blocked by the host firewall
