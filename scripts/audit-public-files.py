#!/usr/bin/env python3
"""Audit index blobs or all reachable history. Findings contain locations/rules, never values."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[1]
MAX_BLOB = 32 * 1024 * 1024
CREDENTIALS = [
    re.compile(rb'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,}|xox[baprs]-[A-Za-z0-9-]{15,})'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    re.compile(rb'(?i)\bauthorization\s*[:=]\s*[\x22\x27]?\s*(?:bearer|basic)\s+[A-Za-z0-9_+=./-]{12,}'),
    re.compile(rb'''(?i)\b(?:api[_-]?key|client[_-]?secret|password|access[_-]?token|session[_-]?token|cookie)\b[\x22\x27]?\s*[:=]\s*[\x22\x27][^\x22\x27\r\n]{12,}[\x22\x27]'''),
    re.compile(rb'''[a-z][a-z0-9+.-]*://[^\s/:'\x22]+:[^\s/@'\x22]{8,}@''', re.I),
]
LOCAL_PATH = re.compile(rb'''/(?:Users|home)/[A-Za-z0-9_.@-]+/|/private/var/folders/[A-Za-z0-9_]{2}/[A-Za-z0-9_]{8,}|[A-Za-z]:\\Users\\[A-Za-z0-9_.@-]+\\''')
MEDIA = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.icns', '.pdf', '.svg', '.svgz'}
SENSITIVE = {'.p8', '.p12', '.pfx', '.pem', '.key', '.mobileprovision', '.har', '.mov', '.mp4', '.m4v', '.sqlite', '.sqlite3', '.db', '.dmg', '.zip', '.tar', '.gz', '.dSYM'}
EXAMPLE_ROOTS = ('Benchmarks/reports/browser-evidence/', 'docs/examples/')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)


def safe_location(value):
    data = value.encode('utf-8', errors='replace')
    for pattern in CREDENTIALS:
        data = pattern.sub(b'<redacted>', data)
    return data.decode('utf-8', errors='replace')


def index_entries(root):
    entries = []
    for item in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not item: continue
        info, name = item.split(b'\t', 1)
        mode, oid, stage = info.decode().split()
        if stage != '0': raise ValueError('Resolve index conflicts before publication')
        entries.append((oid, name.decode('utf-8', errors='replace'), mode))
    return entries


def tree_entries(root, commit):
    result = []
    for item in git(root, 'ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if not item: continue
        info, name = item.split(b'\t', 1)
        mode, kind, oid = info.decode().split()
        result.append((oid, name.decode('utf-8', errors='replace'), mode))
    return result


def load_policy(root):
    path = 'config/publication-policy.json'
    try: return json.loads(git(root, 'show', ':' + path))
    except subprocess.CalledProcessError: return {}


def approved_digest(entry, digest):
    return digest in [entry.get('sha256'), *entry.get('historicalSHA256', [])]


def png_issue(data):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'): return 'invalid PNG'
    offset = 8; kinds = []
    try:
        while offset < len(data):
            size = struct.unpack('>I', data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            payload = data[offset + 8:offset + 8 + size]
            checksum = struct.unpack('>I', data[offset + 8 + size:offset + 12 + size])[0]
            if len(payload) != size or zlib.crc32(kind + payload) != checksum: return 'PNG CRC/length mismatch'
            if kind not in [b'IHDR', b'IDAT', b'IEND', b'sRGB', b'eXIf', b'gAMA', b'cHRM', b'pHYs', b'iCCP']:
                return 'PNG text, timestamp or unreviewed metadata chunk'
            kinds.append(kind); offset += size + 12
        if not kinds or kinds[0] != b'IHDR' or kinds[-1] != b'IEND': return 'incomplete PNG'
    except (struct.error, IndexError): return 'malformed PNG'
    return None


def metadata_issue(data):
    try: value = json.loads(data)
    except (ValueError, UnicodeError): return 'invalid public example JSON'
    private_keys = {'email', 'useremail', 'password', 'apikey', 'authorization', 'cookie', 'cookies', 'accesstoken', 'sessiontoken', 'clientsecret', 'accountsnapshot', 'billing', 'credits', 'conversation', 'messages'}
    def walk(item):
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = re.sub('[^a-z]', '', key.lower())
                if normalized in private_keys: return True
                if key == 'applicationName' and child not in ['Generated fixture', 'Benchmark browser fixture', 'Fixture']:
                    return True
                if key == 'windowTitle' and child: return True
                if walk(child): return True
        elif isinstance(item, list):
            return any(walk(child) for child in item)
        elif isinstance(item, str):
            return bool(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', item))
        return False
    return 'private/unapproved public example metadata' if walk(value) else None


def filename_rules(name):
    p = PurePosixPath(name); suffix = p.suffix.lower(); lower = p.name.lower(); result = []
    if (lower.startswith('.env') and lower != '.env.example' or suffix in {s.lower() for s in SENSITIVE}
            or lower in ['auth.json', 'credentials', 'credentials.json', 'cookies.txt', 'cookies.sqlite', 'id_rsa', 'id_ed25519', '.netrc', '.npmrc']
            or re.search(r'(?:agent[-_]trace|authorization[-_]receipt|account[-_]snapshot|billing[-_]snapshot|education[-_]workspace)', lower)):
        result.append('sensitive-filename')
    if (any(part in ['node_modules', '.build', 'dist', '__pycache__', 'DerivedData', 'runs', 'traces', '.venv'] or part.endswith('.dSYM') for part in p.parts)
            or lower in ['.ds_store', '.coverage'] or suffix in ['.pyc', '.o', '.a', '.profraw', '.log']
            or name.startswith('Benchmarks/reports/') and not name.startswith(EXAMPLE_ROOTS[0])
            or re.match(r'Experiments/[^/]+/reports/', name)):
        result.append('generated-artifact')
    return result


def audit_repository(root, mode='tracked', policy=None):
    root = Path(root).resolve()
    policy = load_policy(root) if policy is None else policy
    approved = policy.get('approvedFiles', {})
    path_examples = policy.get('pathExamples', {})
    current = index_entries(root)
    current_paths = {(oid, name) for oid, name, _ in current}
    metadata = set()
    if mode == 'staged':
        names = set(git(root, 'diff', '--cached', '--name-only', '--diff-filter=ACMRT', '-z').decode().split('\0'))
        entries = [e for e in current if e[1] in names]
    elif mode == 'history':
        if git(root, 'rev-parse', '--is-shallow-repository').strip() == b'true':
            raise ValueError('Historical audit requires a full clone; fetch all branches/tags first')
        entries = set()
        for commit in git(root, 'rev-list', '--all').decode().splitlines():
            entries.update(tree_entries(root, commit)); metadata.add(commit)
        # Annotated tags may carry secrets in their messages too.
        for line in git(root, 'for-each-ref', '--format=%(objectname) %(objecttype)').decode().splitlines():
            oid, kind = line.split()
            if kind == 'tag': metadata.add(oid)
        entries = sorted(entries)
    elif mode == 'tracked': entries = current
    else: raise ValueError('Unknown audit mode')
    findings = []; blobs = {}; seen = set()
    def add(path, oid, rule, location, line=None):
        item = {'path': safe_location(path), 'object': oid, 'rule': rule, 'location': location}
        if line is not None: item['line'] = line
        key = tuple(item.values())
        if key not in seen: findings.append(item); seen.add(key)
    def read(oid):
        if oid not in blobs:
            size = int(git(root, 'cat-file', '-s', oid))
            blobs[oid] = None if size > MAX_BLOB else git(root, 'cat-file', '-p', oid)
        return blobs[oid]
    def content(path, oid, data, location, path_exception=False):
        for pattern in CREDENTIALS:
            for match in pattern.finditer(data): add(path, oid, 'credential', location, data[:match.start()].count(b'\n') + 1)
        if not path_exception:
            for match in LOCAL_PATH.finditer(data): add(path, oid, 'local-path', location, data[:match.start()].count(b'\n') + 1)
    for oid, name, filemode in entries:
        location = 'index' if (oid, name) in current_paths else 'history-only'
        if any(pattern.search(name.encode()) for pattern in CREDENTIALS): add(name, oid, 'credential', location)
        for rule in filename_rules(name): add(name, oid, rule, location)
        if filemode == '160000': add(name, oid, 'unreviewed-submodule', location); continue
        data = read(oid)
        if data is None: add(name, oid, 'oversize-needs-review', location); continue
        if filemode == '120000':
            target = PurePosixPath(data.decode(errors='replace'))
            if target.is_absolute() or '..' in target.parts: add(name, oid, 'unsafe-link', location)
        digest = hashlib.sha256(data).hexdigest()
        if data.startswith((b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'MZ', b'PK\x03\x04', b'\x1f\x8b')):
            add(name, oid, 'compiled-or-archive-artifact', location)
        content(name, oid, data, location, approved_digest(path_examples.get(name, {}), digest))
        needs_review = name.startswith(EXAMPLE_ROOTS) or PurePosixPath(name).suffix.lower() in MEDIA | {'.jsonl'}
        if needs_review and (not approved_digest(approved.get(name, {}), digest) or not approved.get(name, {}).get('purpose')):
            add(name, oid, 'unreviewed-asset', location)
        if name.startswith(EXAMPLE_ROOTS) and name.endswith('.json') and metadata_issue(data):
            add(name, oid, 'example-metadata', location)
        if name.endswith('.png') and png_issue(data): add(name, oid, 'image-metadata', location)
    for oid in sorted(metadata):
        data = read(oid)
        if data is None: add('<git-metadata>', oid, 'oversize-needs-review', 'git-metadata')
        else: content('<git-metadata>', oid, data, 'git-metadata')
    return {'mode': mode, 'filesScanned': len(entries), 'uniqueBlobs': len({e[0] for e in entries}),
            'gitMetadataObjects': len(metadata), 'findings': findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--staged', action='store_true')
    group.add_argument('--history', action='store_true')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        result = audit_repository(args.root, 'staged' if args.staged else 'history' if args.history else 'tracked')
    except (ValueError, TypeError, AttributeError, OSError, subprocess.CalledProcessError):
        print('Publication audit could not complete. Check repository/index/policy validity; no source contents printed.')
        return 2
    if args.json: print(json.dumps(result, indent=2))
    else:
        for finding in result['findings']: print(json.dumps(finding, sort_keys=True))
        print(f"Publication audit ({result['mode']}): {result['filesScanned']} file versions, {result['uniqueBlobs']} blobs, {len(result['findings'])} findings.")
        print('Media pixels need human review; approved hashes do not exempt credential checks.')
    return 1 if result['findings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
