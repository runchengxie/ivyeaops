"""Smoke-test the built or published synthetic compact demo without backend access."""
import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5203/')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        edge = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe'
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        errors, api_requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: api_requests.append(request.url) if '/api/' in request.url else None)
        page.goto(args.url)
        page.get_by_role('heading', name='店铺工作台', exact=True).wait_for()
        page.get_by_text('示例厨房量勺', exact=True).wait_for()
        assert page.get_by_text('模拟对话 · 不连接真实 AI 服务', exact=True).is_visible()
        assert page.evaluate('document.documentElement.scrollHeight <= innerHeight + 1')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(output / 'desktop.png'))
        page.get_by_role('button', name='问助手').first.click()
        editor = page.get_by_role('textbox', name='演示对话输入')
        assert 'demo-v1' in editor.input_value()
        page.get_by_role('button', name='发送').click()
        page.get_by_text('店铺助手 · 演示回复', exact=True).wait_for()
        assert '未执行任何平台' in page.locator('.sw-demo-assistant').inner_text()
        page.get_by_role('button', name='新对话', exact=True).click()
        page.get_by_role('button', name='历史', exact=True).click()
        page.locator('.sw-history button').first.click()
        page.get_by_text('店铺助手 · 演示回复', exact=True).wait_for()
        page.get_by_role('link', name='详情', exact=True).first.click()
        page.get_by_role('heading', name='eMAG 店铺巡检', exact=True).wait_for()
        page.get_by_role('link', name='返回店铺工作台', exact=False).click()
        page.get_by_text('店铺助手 · 演示回复', exact=True).wait_for()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.get_by_role('button', name='对话', exact=True).click()
        assert editor.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(output / 'mobile.png'))
        page.reload()
        assert page.locator('.sw-demo-assistant').count() == 0
        page.get_by_role('heading', name='店铺工作台', exact=True).wait_for()
        assert not api_requests, api_requests
        assert not errors, errors
        browser.close()
    print(json.dumps({'compact_demo': True, 'synthetic_chat_history_details_mobile_reset': True, 'backend_requests': len(api_requests)}))


if __name__ == '__main__':
    main()
