#!/usr/bin/env python3
"""Build a public static site from an explicit documentation allowlist."""
from __future__ import annotations

import argparse
import html
import posixpath
import shutil
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/runchengxie/store-ops'
PAGES = {
    'en': {'index': 'README.md', 'capabilities': 'docs/emag-capability-map.md',
           'architecture': 'docs/architecture.md', 'installation': 'docs/installation.md',
           'configuration': 'docs/configuration.md', 'usage': 'docs/usage.md',
           'operations': 'docs/operations.md'},
    'zh-CN': {'index': 'docs/zh-CN/readme.md', 'capabilities': 'docs/zh-CN/emag-capability-map.md',
              'architecture': 'docs/zh-CN/architecture.md', 'installation': 'docs/zh-CN/installation.md',
              'configuration': 'docs/zh-CN/configuration.md', 'usage': 'docs/zh-CN/usage.md',
              'operations': 'docs/zh-CN/operations.md'},
}
LABELS = {
    'en': {'index': 'Overview', 'capabilities': 'Capabilities', 'architecture': 'Architecture',
           'installation': 'Install', 'configuration': 'Configure', 'usage': 'Use', 'operations': 'Operate'},
    'zh-CN': {'index': '项目介绍', 'capabilities': '能力边界', 'architecture': '架构',
              'installation': '安装', 'configuration': '配置', 'usage': '使用', 'operations': '运维'},
}


class RewriteLinks(Treeprocessor):
    def __init__(self, md, source, output, published):
        super().__init__(md)
        self.source, self.output, self.published = source, output, published

    def run(self, root):
        for element in root.iter('a'):
            href = element.get('href')
            if not href:
                continue
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (self.source.parent / unquote(parsed.path)).resolve()
            try:
                relative = target.relative_to(ROOT)
            except ValueError as exc:
                raise ValueError(f'Link escapes repository: {self.source}: {href}') from exc
            if not target.exists():
                raise ValueError(f'Broken local link: {self.source}: {href}')
            if target in self.published:
                dest = posixpath.relpath(self.published[target], self.output.parent.as_posix())
                element.set('href', urlunsplit(('', '', dest, parsed.query, parsed.fragment)))
            else:
                kind = 'tree' if target.is_dir() else 'blob'
                path = f'/runchengxie/store-ops/{kind}/main/{quote(relative.as_posix(), safe="/")}'
                element.set('href', urlunsplit(('https', 'github.com', path, parsed.query, parsed.fragment)))
        return root


class LinkExtension(Extension):
    def __init__(self, source, output, published):
        super().__init__()
        self.source, self.output, self.published = source, output, published

    def extendMarkdown(self, md):
        md.treeprocessors.register(RewriteLinks(md, self.source, self.output, self.published), 'site-links', 5)


def relative_link(current, destination):
    return posixpath.relpath(destination.as_posix(), current.parent.as_posix())


def build(output, demo_dir=None):
    output = Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f'Output must be an empty directory: {output}')
    published = {(ROOT / source).resolve(): Path(lang, f'{name}.html').as_posix()
                 for lang, pages in PAGES.items() for name, source in pages.items()}
    output.mkdir(parents=True, exist_ok=True)
    if demo_dir is not None:
        if Path(demo_dir).is_symlink():
            raise ValueError('Demo must not be a symbolic link')
        demo = Path(demo_dir).resolve()
        if not (demo / 'index.html').is_file() or any(path.is_symlink() for path in demo.rglob('*')):
            raise ValueError('Demo must be a built directory without symbolic links')
        if demo == output or output in demo.parents or demo in output.parents:
            raise ValueError('Demo source must be outside the output directory')
        shutil.copytree(demo, output / 'demo')
    (output / 'assets').mkdir(exist_ok=True)
    (output / 'assets/site.css').write_text((ROOT / 'docs/site/site.css').read_text('utf-8'), encoding='utf-8')
    (output / 'assets/emag-workbench.png').write_bytes((ROOT / 'docs/site/emag-workbench.png').read_bytes())
    (output / 'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=en/index.html"><title>ivyeaops</title><a href="en/index.html">Open documentation</a></html>', encoding='utf-8')
    for lang, pages in PAGES.items():
        for name, filename in pages.items():
            source = (ROOT / filename).resolve()
            dest = Path(lang, f'{name}.html')
            renderer = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc', LinkExtension(source, dest, published)])
            content = renderer.convert(source.read_text('utf-8'))
            if name == 'index':
                alt = '使用模拟店铺数据的 eMAG 巡检工作台' if lang == 'zh-CN' else 'eMAG inspection workbench using synthetic store data'
                caption = '工作台截图使用模拟数据，界面目前主要为中文。' if lang == 'zh-CN' else 'Workbench preview with synthetic data. The interface is currently mostly Chinese.'
                demo_label = '打开交互演示' if lang == 'zh-CN' else 'Open interactive demo'
                link = f'<p><a class="demo-cta" href="../demo/index.html">{demo_label} →</a></p>' if demo_dir is not None else ''
                preview = f'{link}<figure class="workbench-preview"><img src="../assets/emag-workbench.png" alt="{alt}"><figcaption>{caption}</figcaption></figure>'
                content = content.replace('</h1>', '</h1>' + preview, 1)
            labels = LABELS[lang]
            nav = ''.join(f'<a href="{relative_link(dest, Path(lang, f"{item}.html"))}"{(" aria-current=page" if item == name else "")}>{html.escape(labels[item])}</a>' for item in pages)
            other = 'zh-CN' if lang == 'en' else 'en'
            other_url = relative_link(dest, Path(other, f'{name}.html'))
            other_label = '中文' if lang == 'en' else 'English'
            css = relative_link(dest, Path('assets/site.css'))
            title = html.escape(labels[name])
            skip_label = '跳转到正文' if lang == 'zh-CN' else 'Skip to content'
            nav_label = '文档' if lang == 'zh-CN' else 'Documentation'
            source_note = '带来源的证据' if lang == 'zh-CN' else 'Source-labelled evidence'
            home = relative_link(dest, Path(lang, 'index.html'))
            page = f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Self-hosted eMAG evidence workflows and documentation.">
<title>{title} · ivyeaops</title><link rel="stylesheet" href="{css}"></head>
<body><a class="skip" href="#content">{skip_label}</a><header class="header"><div class="header-inner"><a class="brand" href="{home}"><span class="brand-mark">i</span><span>ivyeaops</span></a><div class="header-actions"><a href="{other_url}" hreflang="{other}">{other_label}</a><a class="github" href="{REPOSITORY}">GitHub ↗</a></div></div></header>
<div class="layout"><aside class="sidebar"><p class="sidebar-label">{nav_label}</p><nav aria-label="{nav_label}">{nav}</nav><div class="sidebar-note">eMAG RO<br><span>{source_note}</span></div></aside><main id="content" class="content"><div class="eyebrow">ivyeaops <span>/</span> {title}</div><article>{content}</article><footer>AGPL-3.0 · <a href="{REPOSITORY}">Source on GitHub</a></footer></main></div></body></html>'''
            target = output / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page, encoding='utf-8')
    print(f'Built {len(published)} documentation pages in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='Output directory for generated static files')
    parser.add_argument('--demo-dir', help='Explicitly include a built, public demo directory')
    args = parser.parse_args()
    build(args.output, args.demo_dir)
