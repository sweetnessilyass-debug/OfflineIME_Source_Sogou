"""Decode the user-supplied, hash-pinned original APK into ignored local storage."""
import hashlib
import subprocess
from build_support import ROOT, ORIGINAL, EXPECTED, required_file, toolchain


def main():
    required_file(ORIGINAL, 'Original APK')
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit('The original APK hash differs from the supported version.')
    _, binaries, _, _, apktool = toolchain()
    target = ROOT / 'audit/decoded'
    if target.exists():
        raise SystemExit('audit/decoded already exists; use the existing decode or inspect it before replacing it.')
    target.parent.mkdir(exist_ok=True)
    subprocess.run([str(binaries['java']), '-jar', str(apktool), 'd', str(ORIGINAL),
        '-o', str(target), '-p', str(ROOT / 'tools/apktool-framework')], check=True)


if __name__ == '__main__':
    main()
