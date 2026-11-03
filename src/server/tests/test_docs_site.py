"""The published documentation build must contain only public, usable pages."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for name, value in attrs if name == 'href' and value)


def test_site_build_has_localized_pages_and_resolves_local_links(tmp_path):
    destination = tmp_path / 'site'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-docs-site.py'), '--output', str(destination)],
                            cwd=tmp_path, capture_output=True, encoding='utf-8', timeout=45)
    assert result.returncode == 0, result.stderr
    assert (destination / 'index.html').is_file()
    assert 'ivyeaops' in (destination / 'en/index.html').read_text('utf-8')
    assert 'https://github.com/runchengxie/store-ops' in (destination / 'en/index.html').read_text('utf-8')
    assert 'eMAG' in (destination / 'zh-CN/index.html').read_text('utf-8')
    assert (destination / 'assets/emag-workbench.png').is_file()
    assert 'synthetic' in (destination / 'en/index.html').read_text('utf-8').lower()
    assert '模拟' in (destination / 'zh-CN/index.html').read_text('utf-8')
    assert not (destination / 'data').exists()
    for page in destination.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text('utf-8'))
        for href in parser.hrefs:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert not parsed.path.startswith('/'), (page, href)
            target = (page.parent / unquote(parsed.path)).resolve()
            assert target.is_file(), (page, href)


def test_site_build_preserves_existing_output(tmp_path):
    destination = tmp_path / 'site'
    destination.mkdir()
    marker = destination / 'existing.txt'
    marker.write_text('keep', encoding='utf-8')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-docs-site.py'), '--output', str(destination)],
                            capture_output=True, encoding='utf-8', timeout=45)
    assert result.returncode != 0
    assert marker.read_text(encoding='utf-8') == 'keep'


def test_site_links_an_explicit_demo_bundle(tmp_path):
    demo = tmp_path / 'built-demo'
    demo.mkdir()
    (demo / 'index.html').write_text('<!doctype html><title>Synthetic demo</title>', encoding='utf-8')
    destination = tmp_path / 'site'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-docs-site.py'), '--output', str(destination),
                             '--demo-dir', str(demo)], capture_output=True, encoding='utf-8', timeout=45)
    assert result.returncode == 0, result.stderr
    assert (destination / 'demo/index.html').is_file()
    assert '../demo/index.html' in (destination / 'en/index.html').read_text('utf-8')
    assert '../demo/index.html' in (destination / 'zh-CN/index.html').read_text('utf-8')


def test_demo_source_cannot_contain_output_directory(tmp_path):
    demo = tmp_path / 'built-demo'
    demo.mkdir()
    (demo / 'index.html').write_text('synthetic', encoding='utf-8')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-docs-site.py'), '--output', str(demo / 'site'),
                             '--demo-dir', str(demo)], capture_output=True, encoding='utf-8', timeout=45)
    assert result.returncode != 0
    assert (demo / 'index.html').read_text('utf-8') == 'synthetic'
