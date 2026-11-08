import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('gitleaks_runner',Path(__file__).resolve().parents[1]/'run-gitleaks.py')
runner=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(runner)


class GitleaksRunnerTests(unittest.TestCase):
    def test_tampered_download_is_rejected_before_executable_creation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner.urllib.request,'urlopen',return_value=io.BytesIO(b'tampered')):
            with self.assertRaisesRegex(ValueError,'checksum'):
                runner.install_tool(tmp,'Darwin','arm64')
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_redaction_and_safe_report_are_mandatory(self):
        secret='ghp_'+'X'*36
        with tempfile.TemporaryDirectory() as tmp:
            def execute(command,**kwargs):
                self.assertIn('--redact=100',command)
                self.assertIn('--ignore-gitleaks-allow',command)
                self.assertIn('--gitleaks-ignore-path',command)
                self.assertIn('--log-opts=--all',command)
                Path(tmp,'findings.json').write_text(json.dumps([{'File':'config.txt','StartLine':3,'RuleID':'github-pat','Commit':'a'*40,'Secret':secret,'Match':secret}]))
                return type('Result',(),{'returncode':1})()
            with patch.object(runner.subprocess,'run',side_effect=execute):
                findings=runner.scan('/tmp/scanner',tmp,tmp)
            self.assertNotIn(secret,json.dumps(findings))
            self.assertEqual(findings[0]['line'],3)

    def test_missing_report_cannot_be_interpreted_as_clean(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner.subprocess,'run',return_value=type('Result',(),{'returncode':0})()):
            with self.assertRaisesRegex(ValueError,'did not complete'):
                runner.scan('/tmp/scanner',tmp,tmp)
