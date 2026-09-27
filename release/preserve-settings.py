"""Make the pinned legacy entrypoint preserve existing Transmission settings."""
from pathlib import Path

path = Path('/scripts/start.sh')
source = path.read_text()
old = '    cp /sources/settings.json /torrents/config/transmission/settings.json\n'
if source.count(old) != 1 or source.count('set -x\n') != 1:
    raise SystemExit('Pinned Transmission startup differs from the reviewed baseline')
source = source.replace(old, '    [ -f /torrents/config/transmission/settings.json ] || cp /sources/settings.json /torrents/config/transmission/settings.json\n')
# Do not emit expanded credentials while invoking the inherited startup script.
source = source.replace('set -x\n', '')
path.write_text(source)
