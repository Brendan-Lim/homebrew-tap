import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('publication_audit', Path(__file__).resolve().parents[1] / 'audit-public-files.py')
audit = importlib.util.module_from_spec(SPEC)


class PublicationAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture Author')
        self.git('config', 'user.email', 'fixture@example.test')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.git('add', '--', name)

    def scan(self, mode='tracked', policy=None):
        return audit.audit_repository(self.root, mode=mode, policy=policy or {})

    def test_staged_blob_is_scanned_even_when_worktree_hides_or_deletes_it(self):
        secret = 'ghp_' + 'A' * 36
        self.write('safe.txt', secret)
        (self.root / 'safe.txt').write_text('clean worktree')
        self.assertIn('credential', {f['rule'] for f in self.scan('staged')['findings']})
        (self.root / 'safe.txt').unlink()
        report = self.scan('staged')
        self.assertIn('credential', {f['rule'] for f in report['findings']})
        self.assertNotIn(secret, json.dumps(report))

    def test_secrets_in_history_and_a_tag_remain_detected_after_head_cleanup(self):
        self.write('old.txt', 'sk-' + 'b' * 40)
        self.git('commit', '-qm', 'fixture with secret')
        self.git('tag', 'fixture-preview')
        self.git('rm', '-q', 'old.txt')
        self.git('commit', '-qm', 'remove fixture secret')
        self.assertEqual(self.scan()['findings'], [])
        findings = self.scan('history')['findings']
        self.assertTrue(any(f['rule'] == 'credential' and f['location'] == 'history-only' for f in findings))

    def test_same_blob_under_different_historical_names_gets_filename_checks(self):
        self.write('notes.txt', 'harmless bytes')
        self.git('commit', '-qm', 'first')
        self.write('.env', 'harmless bytes')
        self.git('commit', '-qm', 'same bytes in private filename')
        self.git('rm', '-q', '.env')
        self.git('commit', '-qm', 'cleanup')
        self.assertTrue(any(f['path'] == '.env' and f['rule'] == 'sensitive-filename' for f in self.scan('history')['findings']))

    def test_generated_and_sensitive_filenames_are_blocked(self):
        names = ['node_modules/pkg/a.js', 'dist/tool', '.env.local', 'signing.pfx', 'Cookies.sqlite',
                 'session.har', 'capture.mov', 'agent-trace.jsonl', 'Benchmarks/runs/test/output.txt']
        for name in names: self.write(name, 'fixture')
        paths = {f['path'] for f in self.scan()['findings']}
        self.assertTrue(set(names).issubset(paths))

    def test_headers_assignment_secrets_and_personal_paths_are_sanitized(self):
        values = ['Bearer ' + 'c' * 32, 'd' * 32, '/Users/' + 'private-audit-person/Project/file']
        self.write('config.txt', 'Authorization: ' + values[0] + '\npassword = "' + values[1] + '"\n' + values[2])
        result = self.scan()
        self.assertTrue({'credential', 'local-path'}.issubset({f['rule'] for f in result['findings']}))
        for value in values: self.assertNotIn(value, json.dumps(result))

    def test_fixture_approval_is_exact_and_does_not_allow_credentials(self):
        import hashlib
        name = 'docs/examples/session.json'
        data = '{"schemaVersion":2,"frames":[],"applicationName":"Generated fixture"}'
        self.write(name, data)
        policy = {'approvedFiles': {name: {'sha256': hashlib.sha256(data.encode()).hexdigest(), 'purpose': 'synthetic fixture'}}}
        self.assertEqual(self.scan(policy=policy)['findings'], [])
        self.write(name, '{"api_key":"' + 'ghp_' + 'e' * 36 + '"}')
        malicious = (self.root / name).read_bytes()
        policy['approvedFiles'][name]['sha256'] = hashlib.sha256(malicious).hexdigest()
        self.assertIn('credential', {f['rule'] for f in self.scan(policy=policy)['findings']})

    def test_new_media_and_unapproved_or_private_example_metadata_fail(self):
        self.write('docs/new-image.png', 'not a real PNG')
        self.write('docs/examples/session.json', '{"email":"person@example.test","applicationName":"Personal browser"}')
        rules = {f['rule'] for f in self.scan()['findings']}
        self.assertIn('unreviewed-asset', rules)
        self.assertIn('example-metadata', rules)

    def test_reviewed_historical_fixture_digests_remain_valid(self):
        import hashlib
        name='docs/examples/session.json'
        first='{"applicationName":"Generated fixture","schemaVersion":1}'
        second='{"applicationName":"Generated fixture","schemaVersion":2}'
        self.write(name,first);self.git('commit','-qm','first reviewed fixture')
        self.write(name,second);self.git('commit','-qm','second reviewed fixture')
        policy={'approvedFiles':{name:{'sha256':hashlib.sha256(second.encode()).hexdigest(),
                                    'historicalSHA256':[hashlib.sha256(first.encode()).hexdigest()],
                                    'purpose':'reviewed synthetic fixture versions'}}}
        self.assertEqual(self.scan('history',policy=policy)['findings'],[])

    def test_synthetic_path_exception_is_bound_to_exact_content(self):
        import hashlib
        name = 'Tests/Fixture.swift'
        self.write(name, 'let path = "' + '/Users/' + 'synthetic-person/Project"')
        data = (self.root / name).read_bytes()
        policy = {'pathExamples': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'reason': 'synthetic quoting test'}}}
        self.assertEqual(self.scan(policy=policy)['findings'], [])
        self.write(name, 'let path = "' + '/Users/' + 'another-person/Project"')
        self.assertIn('local-path', {f['rule'] for f in self.scan(policy=policy)['findings']} )

    def test_empty_staged_set_and_staged_deletion_are_safe(self):
        self.write('readme.txt', 'hello')
        self.git('commit', '-qm', 'initial')
        self.assertEqual(self.scan('staged')['filesScanned'], 0)
        self.git('rm', '-q', 'readme.txt')
        self.assertEqual(self.scan('staged')['findings'], [])

    def test_git_metadata_and_unsafe_symlinks_are_checked(self):
        self.write('file.txt', 'hello')
        self.git('commit', '-qm', 'accidental token ' + 'ghp_' + 'f' * 36)
        (self.root / 'outside').symlink_to('/Users/' + 'private-person/secret')
        self.git('add', 'outside')
        rules = {f['rule'] for f in self.scan('history')['findings']}
        self.assertIn('credential', rules)
        self.assertIn('unsafe-link', {f['rule'] for f in self.scan()['findings']})

    def test_disguised_compiled_artifact_and_secret_in_filename_are_safe_to_report(self):
        token = 'ghp_' + 'z' * 36
        self.write(token + '.txt', 'safe content')
        self.write('innocent-resource', '\x7fELFcompiled fixture')
        report = self.scan()
        self.assertIn('compiled-or-archive-artifact', {f['rule'] for f in report['findings']})
        self.assertTrue(any(f['path'] == '<redacted>.txt' and f['rule'] == 'credential' for f in report['findings']))
        self.assertNotIn(token, json.dumps(report))


def setUpModule():
    SPEC.loader.exec_module(audit)


if __name__ == '__main__':
    unittest.main()
