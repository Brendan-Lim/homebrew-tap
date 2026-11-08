#!/usr/bin/env python3
"""Install/uninstall only on a disposable GitHub-hosted macOS runner; never authorize apps."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

assert os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted', 'Disposable hosted runner only'
assert subprocess.check_output(['uname', '-m'], text=True).strip() == 'arm64'
token = 'Brendan-Lim/tap/contextlens-preview'
app = Path('/Applications/ContextLens.app')
prefix = Path(subprocess.check_output(['brew', '--prefix'], text=True).strip())
cli = prefix / 'bin/contextlens-cli'
assert not app.exists() and not cli.exists() and not cli.is_symlink(), 'Runner already has ContextLens; refusing to touch it'
assert not (prefix / 'Caskroom/contextlens').exists() and not (prefix / 'Caskroom/contextlens-preview').exists()
report = dict(sourceCommit=os.environ['GITHUB_SHA'], runnerOS=subprocess.check_output(['sw_vers', '-productVersion'], text=True).strip(),
              architecture='arm64', homebrew=subprocess.check_output(['brew', '--version'], text=True).strip())


def run(*command, check=True, timeout=120):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    print(result.stdout, end='')
    print(result.stderr, end='')
    if check: result.check_returncode()
    return result


# A foreign app must survive a default installation attempt unchanged.
app.mkdir()
marker = app / 'foreign-installation-marker'
marker.write_text('preserve this existing app')
try:
    conflict = run('brew', 'install', '--cask', token, check=False)
    assert conflict.returncode != 0 and 'already an App' in conflict.stdout + conflict.stderr
    assert marker.read_text() == 'preserve this existing app'
    report['existingAppProtection'] = 'pass'
finally:
    marker.unlink()
    app.rmdir()

session = Path.home() / 'Library/Application Support/ContextLens/Sessions/preview-install-fixture'
assert not session.exists()
session.mkdir(parents=True)
(session / 'session.json').write_text('{"fixture":"preserve on uninstall"}')
with tempfile.TemporaryDirectory(prefix='contextlens-user-export-') as temporary:
    export_marker = Path(temporary) / 'context.md'
    export_marker.write_text('user export must remain')
    try:
        run('brew', 'install', '--cask', token)
        assert (app / 'Contents/MacOS/ContextLens').is_file()
        assert cli.is_symlink() and cli.resolve() == app / 'Contents/MacOS/contextlens-cli'
        report['installationAppAndCLILink'] = 'pass'
        run('codesign', '--verify', '--deep', '--strict', str(app))
        quarantine = run('xattr', '-p', 'com.apple.quarantine', str(app))
        assert quarantine.stdout.strip(), 'Default Homebrew quarantine must be retained'
        report['quarantineRetained'] = 'pass'
        # Assessment is read-only. It is not a human first-launch test.
        assessment = run('spctl', '--assess', '--type', 'execute', '-vv', str(app), check=False)
        report['gatekeeperAssessment'] = dict(returncode=assessment.returncode, output=(assessment.stdout + assessment.stderr).strip())
        try:
            help_result = run(str(cli), '--help', check=False, timeout=15)
            report['installedCLIHelp'] = 'pass' if help_result.returncode == 0 and 'replay' in help_result.stdout else 'blocked/failed; manual authorization pending'
        except subprocess.TimeoutExpired:
            report['installedCLIHelp'] = 'timeout; manual authorization pending'
        report['interactiveFirstLaunchOpenAnywayScreenRecordingCaptureHandOff'] = 'pending; no human/interactive clean macOS environment'
    finally:
        run('brew', 'uninstall', '--cask', token)
    assert not app.exists() and not cli.exists() and not cli.is_symlink()
    assert (session / 'session.json').read_text() == '{"fixture":"preserve on uninstall"}'
    assert export_marker.read_text() == 'user export must remain'
    report['uninstallPreservesSessionsAndExports'] = 'pass'

print(json.dumps(report, indent=2))
Path(os.environ['GITHUB_STEP_SUMMARY']).open('a').write('```json\n' + json.dumps(report, indent=2) + '\n```\n')
