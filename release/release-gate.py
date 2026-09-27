#!/usr/bin/env python3
"""Exercise fresh/restart/upgrade and forwarded TCP/UDP, then check tag absence."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid


def module(filename):
    spec = importlib.util.spec_from_file_location('release_helper', Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


registry = module('registry-check.py')
selector = module('select-peer-port.py')
PREFIX = 'transmission-port-test-' + uuid.uuid4().hex[:12]
containers = []


def docker(*args, check=True):
    result = subprocess.run(['docker', *args], text=True, capture_output=True, timeout=120)
    if check and result.returncode:
        raise RuntimeError(f'Docker {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def free_ports():
    held = []
    try:
        ports = []
        for _ in range(2):
            tcp = socket.socket()
            tcp.bind(('127.0.0.1', 0))
            port = tcp.getsockname()[1]
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind(('127.0.0.1', port))
            held.extend((tcp, udp))
            ports.append(port)
        return ports
    finally:
        for sock in held:
            sock.close()


def helpers():
    for rows in ('combined:42000:42000,tcp:80:43000', 'tcp:80:43000,combined:42000:42000'):
        assert selector.select_port(rows) == 42000
    for rows in ('', 'tcp:80:43000', 'combined:42000:42001,tcp:80:43000',
                 'combined:42000:42000,combined:42001:42001',
                 'combined:0:0,tcp:80:43000', 'udp:42000:42000,tcp:80:43000'):
        try:
            selector.select_port(rows)
        except ValueError:
            pass
        else:
            raise AssertionError('Accepted invalid mapping')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'settings.json'
        for peer, random in [('peer-port', 'peer-port-random-on-start'), ('peer_port', 'peer_port_random_on_start')]:
            path.write_text(json.dumps({peer: 41000, random: True, 'speed-limit-down': 731}))
            path.chmod(0o640)
            selector.update_settings(path, 42000)
            assert json.loads(path.read_text()) == {peer: 42000, random: False, 'speed-limit-down': 731}
            assert path.stat().st_mode & 0o777 == 0o640
    print('PASS mapping validation and settings preservation', flush=True)


def start(name, image, ports, stub, combined, upgraded=False):
    peer, web = ports
    args = ['run', '-d', '--name', name, '--platform', 'linux/amd64',
            '--network', PREFIX, '--init', '--log-driver', 'none',
            '--mount', f'type=volume,src={PREFIX},dst=/torrents',
            '--mount', f'type=bind,src={stub},dst=/release-test/bin,readonly',
            '-e', 'PATH=/release-test/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            '-e', 'INSTANCE_ID=transmission-catalogue-test',
            '-e', 'USERNAME=porttest', '-e', 'PASSWORD=porttest-local-only',
            '-e', f'LISTENING_PORT={web if upgraded else peer}',
            '-p', f'127.0.0.1:{peer}:{peer}/tcp', '-p', f'127.0.0.1:{web}:80/tcp']
    if combined:
        rows = [f'combined:{peer}:{peer}', f'tcp:80:{web}']
        if upgraded:
            rows.reverse()
        args.extend(['-e', 'APPBOX_PORTS=' + ','.join(rows), '-p', f'127.0.0.1:{peer}:{peer}/udp'])
    containers.append(name)
    docker(*args, image)


def rpc(web):
    import base64
    request = urllib.request.Request(f'http://127.0.0.1:{web}/transmission/rpc',
        data=b'{"method":"session-get"}', headers={
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + base64.b64encode(b'porttest:porttest-local-only').decode()})
    try:
        response = urllib.request.urlopen(request, timeout=3)
    except urllib.error.HTTPError as error:
        if error.code != 409:
            raise
        request.add_header('X-Transmission-Session-Id', error.headers['X-Transmission-Session-Id'])
        response = urllib.request.urlopen(request, timeout=3)
    with response:
        payload = json.load(response)
    assert payload['result'] == 'success', payload
    return payload['arguments']


def verify(name, ports, combined, preserved=False):
    peer, web = ports
    bindings = json.loads(docker('inspect', '--format', '{{json .HostConfig.PortBindings}}', name))
    expected = {f'{peer}/tcp', '80/tcp'} | ({f'{peer}/udp'} if combined else set())
    assert set(bindings) == expected, bindings
    deadline = time.monotonic() + 90
    while True:
        try:
            config = rpc(web)
            assert config['peer-port'] == peer and config['peer-port-random-on-start'] is False, config
            assert config['dht-enabled'] and config['utp-enabled']
            if preserved:
                assert config['speed-limit-down'] == 731, config
                assert docker('exec', name, 'cat', '/torrents/catalogue-test-marker') == 'preserved'
            with socket.create_connection(('127.0.0.1', peer), timeout=2):
                pass
            if combined:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
                    udp.settimeout(2)
                    udp.sendto(b'd1:ad2:id20:abcdefghijklmnopqrste1:q4:ping1:t2:ab1:y1:qe', ('127.0.0.1', peer))
                    reply, _ = udp.recvfrom(4096)
                    assert b'1:t2:ab' in reply and b'1:y1:r' in reply
            status = docker('exec', name, 'supervisorctl', 'status')
            states = {line.split()[0]: line.split()[1] for line in status.splitlines() if len(line.split()) > 1}
            assert states.get('transmission') == 'RUNNING', status
            break
        except (AssertionError, OSError, RuntimeError, ValueError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    print(f'PASS {name}: RPC settings, web and peer TCP' + ('; forwarded UDP DHT answered' if combined else ''), flush=True)


def main(image):
    if image != registry.EXPECTED:
        raise SystemExit('Unexpected release image')
    assert docker('image', 'inspect', '--format', '{{.Architecture}}', image) == 'amd64'
    helpers()
    with tempfile.TemporaryDirectory(prefix=PREFIX) as directory:
        stub = Path(directory)
        stub.chmod(0o755)
        curl = stub / 'curl'
        curl.write_text('#!/bin/sh\nprintf "HTTP/1.1 200 OK\\r\\n\\r\\n"\n')
        curl.chmod(0o755)
        docker('network', 'create', PREFIX)
        docker('volume', 'create', PREFIX)
        try:
            fresh = PREFIX + '-fresh'
            ports = free_ports()
            start(fresh, image, ports, stub, True)
            verify(fresh, ports, True)
            docker('restart', fresh)
            verify(fresh, ports, True)
            docker('rm', '-f', fresh)
            containers.remove(fresh)
            # Reset the disposable volume before creating a genuine old install.
            docker('volume', 'rm', PREFIX)
            docker('volume', 'create', PREFIX)
            old = PREFIX + '-old'
            old_ports = free_ports()
            start(old, registry.PREVIOUS, old_ports, stub, False)
            verify(old, old_ports, False)
            docker('exec', old, 'supervisorctl', 'stop', 'transmission')
            code = "import json,pathlib;p=pathlib.Path('/torrents/config/transmission/settings.json');c=json.loads(p.read_text());c['speed-limit-down']=731;p.write_text(json.dumps(c));pathlib.Path('/torrents/catalogue-test-marker').write_text('preserved')"
            docker('exec', old, 'python3', '-c', code)
            docker('stop', old)
            docker('rm', old)
            containers.remove(old)
            upgraded = PREFIX + '-upgraded'
            new_ports = [free_ports()[0], old_ports[1]]
            start(upgraded, image, new_ports, stub, True, upgraded=True)
            verify(upgraded, new_ports, True, preserved=True)
            docker('restart', upgraded)
            verify(upgraded, new_ports, True, preserved=True)
        finally:
            for name in containers:
                docker('rm', '-f', name, check=False)
            docker('volume', 'rm', PREFIX, check=False)
            docker('network', 'rm', PREFIX, check=False)
    registry.require_absent(image)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: release-gate.py IMAGE')
    main(sys.argv[1])
