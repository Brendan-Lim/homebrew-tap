#!/usr/bin/env python3
"""Run a pinned, checksum-verified local Gitleaks scan; print only sanitized locations."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = '8.30.1'
# Official v8.30.1 checksums; temporary tool only, never an app dependency.
ASSETS = {
    ('Darwin', 'arm64'): (378332059, 'b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5'),
    ('Linux', 'x86_64'): (378332058, '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'),
}
SPEC = importlib.util.spec_from_file_location('publication_audit', Path(__file__).with_name('audit-public-files.py'))
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def install_tool(directory, system=None, machine=None):
    key = (system or platform.system(), machine or platform.machine())
    if key not in ASSETS: raise ValueError('Supported scanner hosts: Apple Silicon macOS or Linux x86_64')
    asset_id, checksum = ASSETS[key]
    request = urllib.request.Request(f'https://api.github.com/repos/gitleaks/gitleaks/releases/assets/{asset_id}',
                                    headers={'Accept': 'application/octet-stream', 'User-Agent': 'ContextLens-publication-audit'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError('Pinned Gitleaks archive checksum mismatch; no tool executed')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        member = archive.getmember('gitleaks')
        if not member.isfile() or member.size > 32 * 1024 * 1024: raise ValueError('Unexpected scanner executable')
        binary = archive.extractfile(member).read()
    path = Path(directory) / 'gitleaks'
    path.write_bytes(binary); path.chmod(0o700)
    return path


def scan(binary, root, directory):
    root = Path(root).resolve(); directory = Path(directory)
    config = directory / 'default-rules.toml'
    config.write_text('[extend]\nuseDefault = true\n')
    ignore = directory / 'empty.ignore'; ignore.write_text('')
    report = directory / 'findings.json'
    env = {k: v for k, v in os.environ.items() if not k.startswith('GITLEAKS_')}
    result = subprocess.run([str(binary), 'git', str(root), '--log-opts=--all', '--redact=100', '--no-banner',
                             '--log-level', 'error', '--config', str(config), '--ignore-gitleaks-allow',
                             '--gitleaks-ignore-path', str(ignore), '--report-format', 'json', '--report-path', str(report)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, timeout=300)
    if result.returncode not in [0, 1] or not report.is_file():
        raise ValueError('Gitleaks did not complete; no source output printed')
    findings = json.loads(report.read_text())
    if not isinstance(findings, list) or result.returncode == 1 and not findings:
        raise ValueError('Inconsistent Gitleaks result')
    # Neither Match, Secret, context lines nor commit-author fields leave the temporary report.
    safe = []
    for finding in findings:
        commit = finding.get('Commit', '')
        safe.append({'path': audit.safe_location(str(finding.get('File', '<unknown>'))),
                     'line': int(finding.get('StartLine', 0)), 'rule': audit.safe_location(str(finding.get('RuleID', 'unknown'))),
                     'commit': commit if re.fullmatch('[0-9a-f]{40}', commit) else '<unknown>'})
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix='contextlens-gitleaks-') as temporary:
            binary = install_tool(temporary)
            findings = scan(binary, args.root, temporary)
        print(json.dumps({'scanner': 'Gitleaks ' + VERSION, 'scope': 'all reachable Git history', 'findings': findings}, indent=2))
        return 1 if findings else 0
    except Exception:
        # Network errors can carry signed redirect URLs; never dump exceptions or raw reports.
        print('Gitleaks audit could not complete. Check the pinned download, network and repository; no source values printed.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
