# ADR 003: Release sync for CasaOS

## Status
Accepted

## Context
The image is published to GHCR on every `v*` tag with three tags: the exact version (`1.2.3`), the minor track (`1.2`), and `latest`. The release ZIPs have shipped a version-pinned `docker-compose.yml` since `6dfc081`, but the in-repo `docker-compose.yml` lagged at `:latest`. CasaOS detects updates by comparing the version string in the manifest/compose against what's installed — `:latest` is opaque, so users on the in-repo compose never saw an update prompt even when a new image had shipped.

The fix has to keep the published image, the release ZIP, and the in-repo compose pointing at the same version on every release.

## Decisions

### Pin the in-repo compose to a real version, not `:latest`
**Choice:** `docker-compose.yml` on master pins `ghcr.io/thomasuebel/switch-bedrock:<semver>`. One-time catch-up bump set it to `1.0.0` to match the most recent release.
**Rationale:** `:latest` is invisible to CasaOS's update check. A semver tag in the compose gives CasaOS something to compare. Users who want bleeding-edge can still swap their local compose back to `:latest`.

### Auto-bump on tag push from CI
**Choice:** After the image push succeeds in `docker-publish.yml`, a follow-up step checks out master, rewrites the image line in `docker-compose.yml` with `sed`, and commits + pushes back.
**Rationale:** A manual bump-then-tag flow is the obvious alternative but error-prone — easy to forget, and easy to push a tag whose master compose doesn't match. Putting the bump in CI makes the release process "push a tag" and nothing else.

### Commit straight to master with `[skip ci]`
**Choice:** The bump commit lands on master directly, with `[skip ci]` in the message so it does not re-trigger the workflows.
**Rationale:** The bump is mechanical — there is nothing to review. A PR would either sit unmerged (defeating the point) or get auto-merged (same outcome, more moving parts). `[skip ci]` avoids the recursive-workflow trap that would otherwise build the same image again.

### Keep the `build.sh` sed as a no-op safety net
**Choice:** `build.sh` still rewrites the image tag in its working copy before zipping, even though the in-repo compose will normally already pin the released version.
**Rationale:** If anyone ever pushes a `v*` tag pointing at a commit where master's compose lags (e.g. an out-of-band re-tag, or an early run before the auto-bump landed), the sed in `build.sh` still produces a correctly-pinned ZIP. Cheap insurance.

### Workflow gets `contents: write`
**Choice:** Bump `permissions: contents` from `read` to `write` in `docker-publish.yml`.
**Rationale:** Required for the default `GITHUB_TOKEN` to push the bump commit. Scoped to the one job that needs it.

## Consequences
- Releasing is "push a `v*` tag". The image, the release ZIP, and the in-repo compose end up at the same version without manual sync.
- Anyone who installed via a pre-pin compose at `:latest` will not see the v1.0.0 → v1.0.1 transition until they swap their compose at least once. After that, all subsequent bumps surface normally.
- If branch protection on master blocks `github-actions[bot]` from pushing, the auto-bump will fail silently (the ZIP and image still publish, only the in-repo compose lags). The escape hatches are either to exempt the bot or switch the bump to a PR via `peter-evans/create-pull-request`.
- A re-tag of an old version would *downgrade* the in-repo compose. We accept this; re-tagging is rare and the bump is one revert away.
