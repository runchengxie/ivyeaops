"""Verify that everyday chat controls are simple and advanced options remain reachable."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as playwright:
        edge = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe'
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        page.goto('http://127.0.0.1:5202/?r=/workbench&wbcase=minimal-many')
        page.locator('.sw-chat-body textarea').wait_for()
        options = page.get_by_role('button', name='选项', exact=True)
        assert options.count() == 1, 'The simple composer needs one explicit Options entry'
        assert options.get_attribute('aria-expanded') == 'false'
        assert not page.get_by_label('审批档位', exact=True).is_visible()
        assert page.locator('.cc-minimal-status').inner_text() == '仅分析'
        assert page.locator('.sw-suggestion').count() == 3
        assert page.locator('.sw-eyebrow:visible').count() == 0
        assert 'demo-v1' not in page.locator('body').inner_text()
        options.click()
        assert page.get_by_label('审批档位', exact=True).is_visible()
        assert page.get_by_label('工作区', exact=True).is_visible()
        page.get_by_label('审批档位', exact=True).click()
        page.get_by_role('option', name='完全放行', exact=False).click()
        options.click()
        assert '完全放行' in page.locator('.cc-minimal-status').inner_text()
        options.click()
        page.get_by_label('审批档位', exact=True).click()
        page.get_by_role('option', name='只读', exact=False).click()
        options.click()
        assert not page.get_by_label('审批档位', exact=True).is_visible()
        assert page.get_by_role('button', name='发送', exact=True).is_visible()
        assert page.evaluate('window.__lastChatBody === undefined')
        editor = page.locator('.sw-chat-body textarea')
        editor.fill('/model')
        page.locator('.cc-menu-item').filter(has_text='模型 · 切换主脑').wait_for()
        editor.press('Enter')
        page.wait_for_function("document.querySelector('.cc-minimal-options').getAttribute('aria-expanded') === 'true'")
        assert options.get_attribute('aria-expanded') == 'true'
        assert page.locator('.sw-workbench').evaluate('element => element.getBoundingClientRect().bottom <= innerHeight + 1')
        page.get_by_role('heading', name='店铺工作台', exact=True).click()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.get_by_role('button', name='对话', exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.goto('http://127.0.0.1:5202/?r=/console')
        page.locator('.cc-composer').wait_for()
        assert page.get_by_label('审批档位', exact=True).is_visible()
        assert page.get_by_role('button', name='选项', exact=True).count() == 0
        browser.close()
    print(json.dumps({'minimal_controls': True, 'advanced_options_and_model_command': True, 'three_priorities': True, 'mobile_fit': True}))


if __name__ == '__main__':
    main()
