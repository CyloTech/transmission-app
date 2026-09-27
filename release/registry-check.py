#!/usr/bin/env python3
"""Require an authenticated, definitive absent release tag before publication."""
import subprocess
import sys

EXPECTED = 'repo.cylo.net/transmission:4.1.2-1'
PREVIOUS = 'repo.cylo.net/transmission@sha256:dec1ad496b060c70785d8275b434f02bfe47217bed37e4c04bf011c9dc3893fd'


def require_absent(image):
    if image != EXPECTED:
        raise RuntimeError('Unexpected image reference')
    known = subprocess.run(['docker', 'manifest', 'inspect', PREVIOUS], capture_output=True, text=True, timeout=60)
    if known.returncode:
        raise RuntimeError('Registry baseline read failed; state is indeterminate')
    result = subprocess.run(['docker', 'manifest', 'inspect', image], capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        raise RuntimeError('Release tag exists; refusing replacement')
    if result.stderr.strip() != 'no such manifest: ' + image:
        raise RuntimeError('Registry did not report definitive tag absence; refusing publication')
    print('Registry verified: baseline readable; release tag definitively absent', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: registry-check.py IMAGE')
    require_absent(sys.argv[1])
