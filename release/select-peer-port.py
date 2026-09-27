"""Resolve the version-scoped Appbox port records before Transmission starts."""
import json
import os
from pathlib import Path
import stat
import tempfile


def select_port(value):
    rows = value.split(',')
    if len(rows) != 2:
        raise ValueError('Expected one combined peer port and one TCP web port')
    peers = []
    web = 0
    for row in rows:
        fields = row.split(':')
        if len(fields) != 3:
            raise ValueError('Invalid Appbox port record')
        protocol, internal, external = fields
        if not internal.isascii() or not external.isascii() or not internal.isdecimal() or not external.isdecimal():
            raise ValueError('Appbox ports must be numeric')
        internal, external = int(internal), int(external)
        if not (1 <= internal <= 65535 and 1 <= external <= 65535):
            raise ValueError('Appbox port is out of range')
        if protocol == 'combined' and internal == external:
            peers.append(internal)
        elif protocol == 'tcp' and internal == 80:
            web += 1
        else:
            raise ValueError('Unexpected Appbox port mapping')
    if len(peers) != 1 or web != 1:
        raise ValueError('Expected one combined peer port and one TCP web port')
    return peers[0]


def update_settings(path, port):
    if not path.exists():
        return
    previous = path.stat()
    config = json.loads(path.read_text())
    # Support the persisted spelling used by either Transmission config format.
    for old, new, value in [('peer-port', 'peer_port', port),
                            ('peer-port-random-on-start', 'peer_port_random_on_start', False)]:
        keys = [key for key in (old, new) if key in config] or [old]
        for key in keys:
            config[key] = value
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.appbox-ports-', delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(config, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
            os.chmod(temporary, stat.S_IMODE(previous.st_mode))
            os.chown(temporary, previous.st_uid, previous.st_gid)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    try:
        port = select_port(os.environ.get('APPBOX_PORTS', ''))
        update_settings(Path('/torrents/config/transmission/settings.json'), port)
    except (ValueError, OSError) as error:
        raise SystemExit('Transmission port setup failed: ' + str(error))
    os.environ['LISTENING_PORT'] = str(port)
    os.execv('/scripts/start.sh', ['/scripts/start.sh'])


if __name__ == '__main__':
    main()
