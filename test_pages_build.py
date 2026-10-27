import json
import os
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from scripts.build_pages import build


class LocalLinksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'href', 'src'} and value:
                self.references.append(value)


class PagesBuildTests(unittest.TestCase):
    def test_builds_static_app_routes_assets_and_runtime_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            build(output, '/demo/', 'https://api.example.com')

            expected_pages = (
                'index.html',
                'attacks/index.html',
                'configure/brute_force/index.html',
                'configure/rule_based/index.html',
                'simulation/hybrid/index.html',
                'report/index.html',
            )
            for relative_path in expected_pages:
                self.assertTrue((output / relative_path).is_file(), relative_path)
            self.assertTrue((output / '.nojekyll').is_file())

            index = (output / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<base href="/demo/">', index)
            self.assertIn('static/css/style.css', index)
            self.assertNotIn("{{ url_for(", index)

            config = (output / 'static/js/runtime-config.js').read_text(encoding='utf-8')
            self.assertIn('"API_BASE_URL": "https://api.example.com"', config)
            self.assertIn('"APP_BASE_PATH": "/demo/"', config)
            self.assertTrue((output / 'static/js/simulator.js').is_file())

            for page in output.rglob('*.html'):
                parser = LocalLinksParser()
                parser.feed(page.read_text(encoding='utf-8'))
                for reference in parser.references:
                    resolved = urlsplit(urljoin('https://pages.example/demo/', reference))
                    if resolved.netloc != 'pages.example':
                        continue
                    local_path = resolved.path.removeprefix('/demo/').lstrip('/')
                    target = output / local_path
                    if target.is_dir():
                        target /= 'index.html'
                    self.assertTrue(target.is_file(), f'{page.relative_to(output)} -> {reference}')

    def test_unset_optional_base_path_uses_repository_name(self):
        from unittest.mock import patch
        from scripts.build_pages import default_base_path

        with patch.dict(os.environ, {'PAGES_BASE_PATH': '', 'GITHUB_REPOSITORY': 'owner/project-app'}):
            self.assertEqual(default_base_path(), '/project-app/')
        with patch.dict(os.environ, {'PAGES_BASE_PATH': '', 'GITHUB_REPOSITORY': 'owner/owner.github.io'}):
            self.assertEqual(default_base_path(), '/')


if __name__ == '__main__':
    unittest.main()
