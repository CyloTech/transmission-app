# Transmission 4.1.2-1 validation

Validated 2026-09-27 on the dedicated amd64 builder.

- Build source: pushed commit `6170a37e3e7228d737688e0afeae2a5b4253bcfe`.
- Archive SHA256: `7ff8ee1d83d1203ad87a92cdcac54fbe3e0d3f2267c1bbb0f88daa18434dde06`.
- Published image: `repo.cylo.net/transmission:4.1.2-1`.
- Registry index digest: `sha256:667edf15f1eb12e5f6af50c51301877a6eaeaf7e347fd1ea579101b3de808c4c`.
- Verified amd64 manifest: `sha256:6f366e613e04b2999cb1ecb0ad41838dc625743e8b0f3cb998fa75f429476644`.
- Authenticated registry reads confirmed the new tag absent before build and immediately before push.
- Release gate passed protocol selection in either order, malformed mapping rejection,
  and settings preservation for kebab-case and snake_case keys.
- Fresh installation and restart passed: RPC settings, web interface, peer TCP,
  and a real DHT response through the published UDP peer port.
- Upgrade from the pinned published 4.1.2 image and restart passed the same checks.
  The upgrade test retained the web port, assigned a new combined peer port,
  reversed the allocation-row order, and passed an intentionally wrong legacy
  LISTENING_PORT. The wrapper selected the correct combined allocation.
- Persistent test data and a nondefault download speed setting survived the upgrade.
- Central port reconciliation suite: 53 tests, 170 assertions passed.
- Disposable containers, volume, network and remote build directory were removed.

Catalogue baseline: app 77, version 1242 (`4.1.2`). The app-level version/tag
were still `4.1.0`; publication synchronizes them to `4.1.2-1`. Resources retain
the baseline's one app slot, zero memory/swap/reservation/CPU/PID limits,
init enabled, unprivileged state and null minimum/capability overrides.
App-level fields outside version, tag, port counts and update timestamp are
guarded by a pre-import snapshot hash.

Import `catalog/appbox.yml` with `--import-version --app-id=77 --admin-only`,
without `--set-default`. Review its dry run, then run the Git-delivered
`catalog/publish.sql` in a transaction. Publication supplies the version-scoped
APPBOX_PORTS template and customer release notes before making it public/default.
The global LISTENING_PORT template remains available to older versions.

Publication completed: version ID `1337` is enabled, public and the sole default.
The migration ran from Git commit `7d1f0652d675e0c79fc68f96142f0f52ba98ceaa`.
Independent PostgreSQL readback confirmed the image digest, release notes, both
app and version port counts, and version-specific environment row `808`.
Resource comparison against version `1242` returned true. Hashes of all older
version rows (excluding default/update timestamp) and other app-level fields
matched their pre-import snapshots. Existing global environment row `75` was
unchanged. The original developer checkout's dirty and untracked work was
preserved.

These tests use disposable builder instances. Publication does not update an
existing customer installation or prove that the reported torrent speeds will
change; that also depends on the swarm and network path.
