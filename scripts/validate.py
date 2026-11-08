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
if cask.exists():
    actual = cask.read_text()
    version = re.search(r'^  version "([0-9]+\.[0-9]+\.[0-9]+)"$', actual, re.M)
    checksum = re.search(r'^  sha256 "([a-f0-9]{64})"$', actual, re.M)
    assert version and checksum, 'Real version and final-asset SHA-256 required'
    assert actual == text.replace('__VERSION__', version[1]).replace('__SHA256__', checksum[1])
    subprocess.run(['ruby', '-c', str(cask)], check=True)
    print('Cask syntax and release metadata validated; run Homebrew audit and clean installation separately.')
else:
    print('Pending template syntax validated. No installable cask or release is claimed.')
