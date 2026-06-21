# ADR 002: Dashboard operational features

## Status
Accepted

## Context
The base dashboard (ADR 001) lets the user point GeyserMC at a Java server. As soon as we wanted the dashboard to also *show* runtime state — what version of GeyserMC is installed, whether an update exists, whether the configured remote is reachable and who's online — we hit two new shapes of problem: managing installed binaries from inside the container, and querying an external Java server cheaply enough to render on every page load. This ADR captures the choices made for both.

## Decisions

### JSON sidecar next to the JAR for "what build is installed"
**Choice:** Write `Geyser.jar.meta.json` alongside the JAR at download time; read it back when the dashboard asks for the local version.
**Rationale:** GeyserMC ships build metadata via the build API but does not stamp the JAR with a machine-readable version we can read without unzipping. Parsing the JAR's internal manifest or `git.properties` works but breaks if upstream changes the format. The sidecar captures the entire API response, so we can surface the version, build number, channel, and (if needed) changelogs without any introspection.

### Atomic swap on update
**Choice:** Download to `Geyser.jar.new`, then `os.replace()` onto `Geyser.jar`, then write the sidecar.
**Rationale:** A network failure halfway through a download must not destroy the working JAR. `os.replace()` is atomic on POSIX. The sidecar is written *after* the replace so a half-completed update can't leave the sidecar pointing at a build the JAR doesn't have.

### One-click update, not scheduled
**Choice:** The dashboard shows "Update available" and the user clicks; we do not poll-and-auto-upgrade.
**Rationale:** A bad upstream build would leave the bridge non-booting at an arbitrary time. The owner of a homelab service should choose when to take downtime. The version check is cheap (cached 1h), so showing the indicator costs nothing.

### Declarative `sources.yml`
**Choice:** Adding a new managed JAR is a `sources.yml` edit, not a code change.
**Rationale:** GeyserMC and Floodgate were the first two but the pattern (metadata URL + download URL + jar path + installable flag) generalises. Floodgate sits in the same file but with `installable: false` because it runs on the Java server, not the bridge — the dashboard shows its latest version as information only.

### Restart via `pkill`, not a managed update path
**Choice:** After replacing the JAR we `pkill -f Geyser.jar`; the existing `entrypoint.sh` while-true loop restarts it.
**Rationale:** Reuses the same restart mechanism the config-save flow already relies on (ADR 001). No new supervisor logic, and the only state we depend on is the entrypoint loop that's already running.

### `mcstatus` for the Java server status query
**Choice:** Use the [`mcstatus`](https://pypi.org/project/mcstatus/) library for Server List Ping rather than hand-rolling the protocol.
**Rationale:** Server List Ping is a small wire protocol but the surface around it is wider than expected: SRV records (`_minecraft._tcp.host`), legacy 1.6 servers, Forge mod lists, and MOTD format codes. mcstatus handles all of these. The cost is one Python dependency.

### 60-second server-side cache, 60-second client poll
**Choice:** `server_info.query()` caches per `(host, port)` for 60 s; the dashboard polls `/api/server-info` every 60 s.
**Rationale:** A typical dashboard view is "open it, look, close it". Caching means concurrent or repeated requests in that window don't hammer the upstream. A 60 s poll on the client gives a responsive feeling without measurable load on the remote. The cache TTL and the poll interval match so two open tabs don't double-query.

### Drop the server-info cache when config changes
**Choice:** `POST /api/config` calls `server_info.clear_cache()` after writing the new remote.
**Rationale:** Without this, the dashboard would show stats from the *previous* server for up to 60 s after a config change. Worth the extra line.

## Consequences
- The dashboard does network I/O on `/api/versions` and `/api/server-info`. Both fail soft: errors are rendered, not raised. The 1 h and 60 s caches mean upstream outages aren't immediately visible.
- The bridge can update itself, but the update path depends on the entrypoint loop being alive. If the loop dies, an update succeeds but no GeyserMC will be running until the container is restarted. Acceptable for a homelab service; documented here so a future reader doesn't assume the update path is self-healing.
- Adding a managed binary (e.g. a different proxy) is a config change in `sources.yml` plus, if it needs to install rather than just report, a `pkill` target. The pattern does not generalise to non-jar binaries without code work.
