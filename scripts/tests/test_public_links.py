import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('public_links',Path(__file__).resolve().parents[1]/'check-public-links.py')
links=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(links)


class PublicLinkTests(unittest.TestCase):
    def test_balanced_parentheses_in_apple_documentation_url_are_preserved(self):
        url='https://developer.apple.com/documentation/screencapturekit/sccontentfilter/init(desktopindependentwindow:)'
        self.assertEqual(links.inline_links('[Apple]('+url+')'),[(0,url)])

    def test_ignored_local_report_does_not_satisfy_public_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);subprocess.run(['git','init','-q',tmp],check=True)
            (root/'README.md').write_text('[report](private.md)\n')
            (root/'private.md').write_text('private local evidence')
            subprocess.run(['git','-C',tmp,'add','README.md'],check=True)
            result=links.check_repository(root)
            self.assertEqual(len(result['findings']),1)
            self.assertEqual(result['findings'][0]['reason'],'local destination is not tracked/public')

    def test_reference_links_anchors_and_fences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);subprocess.run(['git','init','-q',tmp],check=True)
            (root/'README.md').write_text('# Heading\n[ok][target]\n[target]: #heading\n[bad](#missing)\n```md\n[example](not-a-link.md)\n```\n')
            subprocess.run(['git','-C',tmp,'add','README.md'],check=True)
            result=links.check_repository(root)
            self.assertEqual(len(result['findings']),1)
            self.assertEqual(result['findings'][0]['reason'],'Markdown heading anchor does not exist')

    def test_relative_directory_root_and_percent_encoded_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);subprocess.run(['git','init','-q',tmp],check=True)
            (root/'docs').mkdir();(root/'A B.md').write_text('# A\n')
            (root/'docs/README.md').write_text('[a](../A%20B.md#a)\n[root](/A%20B.md)\n[dir](../docs/)\n')
            subprocess.run(['git','-C',tmp,'add','.'],check=True)
            self.assertEqual(links.check_repository(root)['findings'],[])
