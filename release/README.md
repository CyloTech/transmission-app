# Transmission 4.1.2-1

Build the `release/` context on the dedicated amd64 builder. The pinned published
4.1.2 image is the runtime baseline; the legacy root Dockerfile is not used for
this packaging release.

The new version uses one dynamic combined TCP/UDP peer port and the existing
static TCP port 80 for the web interface. Its version-scoped `APPBOX_PORTS`
environment template passes protocol, internal port and external port for both
allocations. `select-peer-port.py` validates the mapping and selects the combined
allocation irrespective of row order. This handles both a new installation and
an upgrade that retains an older web-port row.

Existing settings are retained, with only the peer port and random-port setting
updated. Fresh installs still use the baseline configuration and credentials.
Startup shell tracing is disabled to avoid logging expanded credentials.

Before building, run `python3 release/registry-check.py repo.cylo.net/transmission:4.1.2-1`.
Build from a reviewed archive of the pushed commit, then run
`./release/release-gate.py repo.cylo.net/transmission:4.1.2-1` immediately before push.
The gate uses disposable containers, a volume, a network, dummy credentials and
a stubbed installation callback. It checks fresh installation, restart and
upgrade from the published baseline, including settings preservation and an
actual DHT response through the forwarded UDP port. Empty clients may query
public DHT bootstrap nodes. No customer data or production callback is used.

Catalogue publication is separate from image publication. Existing instances
receive this change only through the normal Appbox update flow.
