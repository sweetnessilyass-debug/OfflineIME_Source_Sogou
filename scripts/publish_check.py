"""Inspect staged source or every local revision without printing sensitive values."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
ROOT_FILES = {'.gitignore', '.gitattributes', 'README.md', 'NOTICE.md', 'LICENSE',
              'build_support.py', 'prepare.py'}
SPECIAL_FILES = {'.githooks/pre-push', 'offline-voice/resource-manifest.json',
                 'scripts/publish_check.py'}
SOURCE_DIRS = {'lite', 'offline-voice'}
PRIVATE_PARTS = {'private', 'build', 'work', 'logs', 'device', 'resources', '__pycache__'}
PATTERNS = {
    'absolute Windows path': re.compile(r'(?i)\b[a-z]:[\\/]'),
    'personal Unix home': re.compile(r'/(?:home|Users)/[^\s/]+/'),
    'private key': re.compile(r'-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    'AWS access key': re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    'email address': re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def allowed(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or any(x in PRIVATE_PARTS for x in p.parts):
        return False
    if name in ROOT_FILES | SPECIAL_FILES:
        return True
    return len(p.parts) > 1 and p.parts[0] in SOURCE_DIRS and p.suffix in {'.py', '.java'}


def check(name, data, mode):
    errors = []
    if mode not in {'100644', '100755'} or not allowed(name):
        return ['unexpected path or file mode']
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return ['binary content']
    if '\0' in text:
        errors.append('binary content')
    for label, pattern in PATTERNS.items():
        if pattern.search(text):
            errors.append(label)
    return errors


def inspect(history=False):
    failures = []
    count = 0
    seen = set()
    revisions = git('rev-list', '--all').decode().splitlines() if history else [None]
    if not revisions:
        raise SystemExit('No commits to inspect; stage source and run without --history first.')
    for rev in revisions:
        records = git('ls-tree', '-rz', rev) if rev else git('ls-files', '--stage', '-z')
        for record in records.split(b'\0'):
            if not record:
                continue
            header, raw_name = record.split(b'\t', 1)
            name = raw_name.decode('utf-8')
            fields = header.decode().split()
            mode, oid = (fields[0], fields[2]) if rev else (fields[0], fields[1])
            identity = (name, oid, mode)
            if identity in seen:
                continue
            seen.add(identity)
            count += 1
            for reason in check(name, git('cat-file', 'blob', oid), mode):
                failures.append(f'{name}: {reason}')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        raise SystemExit('Publication check failed; values have not been printed.')
    print(f'Publication check passed: {count} source versions inspected.')


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--history']):
        raise SystemExit('Usage: python scripts/publish_check.py [--history]')
    inspect('--history' in sys.argv)
