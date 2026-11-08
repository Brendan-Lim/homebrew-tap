#!/usr/bin/env python3
"""Validate pending template or a real cask; never fabricate an installable cask."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
template = root / 'Casks/contextlens.rb.in'
cask = root / 'Casks/contextlens.rb'
text = template.read_text()
assert text.count('__VERSION__') == text.count('__SHA256__') == 1
assert ':no_check' not in text
for stanza in ['depends_on arch: :arm64', 'depends_on macos: ">= :sonoma"', 'app "ContextLens.app"', 'binary "#{appdir}/ContextLens.app/Contents/MacOS/contextlens-cli"']:
    assert stanza in text, stanza
subprocess.run(['ruby', '-c', str(template)], check=True)
if cask.exists() and 'Unnotarized' not in cask.read_text():
    actual = cask.read_text()
    version = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+)"$', actual, re.M)
    checksum = re.search(r'^  sha256 "([a-f0-9]{64})"$', actual, re.M)
    assert version and checksum, 'Real version and final-asset SHA-256 required'
    assert actual == text.replace('__VERSION__', version[1]).replace('__SHA256__', checksum[1])
    subprocess.run(['ruby', '-c', str(cask)], check=True)
    print('Cask syntax and release metadata validated; run Homebrew audit and clean installation separately.')
elif not cask.exists():
    print('Pending stable template syntax validated. No installable stable cask is present in this checkout.')

official = root / 'Casks/contextlens-unnotarized.rb.in'
if official.exists():
    template = official.read_text()
    assert template.count('__VERSION__') == template.count('__SHA256__') == template.count('__ASSET_ID__') == 1
    for stanza in ['cask "contextlens"', 'conflicts_with cask: "contextlens-preview"',
                   'depends_on arch: :arm64', 'depends_on macos: :sonoma',
                   'app "ContextLens.app"', 'binary "#{appdir}/ContextLens.app/Contents/MacOS/contextlens-cli"',
                   'Unnotarized official', 'Open Anyway', 'container type: :zip']:
        assert stanza in template, stanza
    for forbidden in [':no_check', 'zap ', 'xattr ', 'spctl ', '--no-quarantine']:
        assert forbidden not in template, forbidden
    subprocess.run(['ruby', '-c', str(official)], check=True)
    if cask.exists() and 'Unnotarized' in cask.read_text():
        actual = cask.read_text()
        version = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+),([1-9][0-9]*)"$', actual, re.M)
        checksum = re.search(r'^  sha256 "([a-f0-9]{64})"$', actual, re.M)
        assert version and checksum, 'Real official version, checksum and asset ID required'
        assert actual == template.replace('__VERSION__', version[1]).replace('__SHA256__', checksum[1]).replace('__ASSET_ID__', version[2])
        subprocess.run(['ruby', '-c', str(cask)], check=True)

preview_template = root / 'Casks/contextlens-preview.rb.in'
if preview_template.exists():
    preview = preview_template.read_text()
    assert preview.count('__VERSION__') == preview.count('__SHA256__') == preview.count('__ASSET_ID__') == 1
    for stanza in ['cask "contextlens-preview"', 'conflicts_with cask: "contextlens"',
                   'depends_on arch: :arm64', 'depends_on macos: :sonoma',
                   'app "ContextLens.app"', 'binary "#{appdir}/ContextLens.app/Contents/MacOS/contextlens-cli"',
                   'Unnotarized', 'Open Anyway', 'header: "Accept: application/octet-stream"', 'container type: :zip']:
        assert stanza in preview, stanza
    for forbidden in [':no_check', 'zap ', 'xattr ', 'spctl ', '--no-quarantine']:
        assert forbidden not in preview, forbidden
    subprocess.run(['ruby', '-c', str(preview_template)], check=True)
    actual_path = root / 'Casks/contextlens-preview.rb'
    if actual_path.exists():
        actual = actual_path.read_text()
        version = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+-preview\.[1-9][0-9]*),([1-9][0-9]*)"$', actual, re.M)
        checksum = re.search(r'^  sha256 "([a-f0-9]{64})"$', actual, re.M)
        assert version and checksum, 'Real preview version, SHA-256 and asset ID required'
        assert actual == preview.replace('__VERSION__', version[1]).replace('__SHA256__', checksum[1]).replace('__ASSET_ID__', version[2])
        subprocess.run(['ruby', '-c', str(actual_path)], check=True)
        print('Preview cask syntax/metadata validated; installation and authorization are separate checks.')
