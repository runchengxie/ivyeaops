"""Verify the compact workbench in the real App harness and isolated browser."""
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE = "http://127.0.0.1:5202"
OUTPUT = Path(os.environ.get("WORKBENCH_QA_DIR", str(Path(tempfile.gettempdir()) / "store-ops-workbench-qa")))


def visit(page, query="wbcase=multi", width=1366, height=768):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{BASE}/?r=/workbench&{query}")
    page.get_by_role("heading", name="店铺工作台", exact=True).wait_for()


def layout(page):
    return page.evaluate("""() => {
      const rect = selector => { const r=document.querySelector(selector).getBoundingClientRect(); return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; };
      return {view:{width:innerWidth,height:innerHeight},doc:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},main:rect('.sw-workbench'),chat:rect('.sw-chat'),left:rect('.sw-left'),sidebar:!!document.querySelector('.app>.sb')};
    }""")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = {}
    with sync_playwright() as playwright:
        edge = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        context = browser.new_context()
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width, height in ((1366, 768), (1440, 900)):
            visit(page, width=width, height=height)
            page.get_by_text("Demo product", exact=True).wait_for()
            page.locator('.sw-chat-body textarea').wait_for()
            measured = layout(page)
            assert measured['doc']['width'] <= width, measured
            assert measured['doc']['height'] <= height + 1, measured
            assert measured['chat']['bottom'] <= height + 1, measured
            assert not measured['sidebar'], measured
            assert page.evaluate('window.__lastChatBody === undefined')
            page.screenshot(path=str(OUTPUT / f"desktop-{width}.png"))
            results[f"layout_{width}"] = measured

        page.get_by_role('button', name='让 AI 分析').first.click()
        textarea = page.locator('.sw-chat-body textarea')
        assert 'demo-ro' in textarea.input_value()
        assert 'demo-v1' in textarea.input_value()
        assert page.evaluate('window.__lastChatBody === undefined')
        page.locator('.sw-chat-body .cc-send').click()
        page.wait_for_function('window.__lastChatBody?.message')
        sent = page.evaluate('window.__lastChatBody')
        assert 'demo-ro' in sent['system'] and 'demo-v1' in sent['system']
        page.locator('.sw-chat-body .cc-stop-secondary').wait_for()
        page.get_by_label('工作台店铺', exact=True).select_option('second-ro')
        assert page.get_by_text('Demo product', exact=True).count() == 0
        page.get_by_text('Second store item', exact=True).wait_for()
        assert 'demo-ro' in page.locator('.sw-chat-scope').inner_text()
        assert page.get_by_role('button', name='为 second-ro 新建对话').is_disabled()
        page.locator('.sw-chat-body .cc-stop-secondary').click()
        page.get_by_role('button', name='为 second-ro 新建对话').wait_for(state='visible')
        page.wait_for_function("!document.querySelector('.sw-scope-warning button').disabled")
        page.get_by_role('button', name='为 second-ro 新建对话').click()
        page.wait_for_function("document.querySelector('.sw-chat-scope').textContent.includes('second-ro')")
        page.get_by_role('button', name='让 AI 分析').first.click()
        page.wait_for_function("document.querySelector('.sw-chat-body textarea').value.includes('SECOND-SKU')")
        assert 'SECOND-SKU' in textarea.input_value()
        page.locator('.sw-chat-body .cc-send').click()
        page.wait_for_function("window.__lastChatBody?.system.includes('second-snapshot')")
        assert 'second-ro' in page.evaluate('window.__lastChatBody.system')
        page.locator('.sw-chat-body .cc-stop-secondary').wait_for()
        page.locator('.sw-chat-body .cc-stop-secondary').click()
        page.wait_for_function("!document.querySelector('.sw-chat-actions button').disabled")
        results['scope_prefill_send_stop'] = True

        page.get_by_role('link', name='查看详情').first.click()
        page.get_by_role('heading', name='eMAG 店铺巡检', exact=False).wait_for()
        page.go_back()
        page.get_by_role('heading', name='店铺工作台', exact=True).wait_for()
        assert 'second-ro' in page.locator('.sw-chat-scope').inner_text()
        results['detail_return_preserves_scope'] = True

        visit(page, width=390, height=844)
        page.get_by_role('button', name='建议', exact=True).click()
        page.get_by_role('button', name='让 AI 分析').first.click()
        assert page.get_by_role('button', name='对话', exact=True).get_attribute('aria-pressed') == 'true'
        textarea = page.locator('.sw-chat-body textarea')
        assert 'demo-ro' in textarea.input_value()
        page.get_by_role('button', name='概况', exact=True).click()
        page.get_by_role('button', name='对话', exact=True).click()
        assert 'demo-ro' in textarea.input_value()
        measured = layout(page)
        assert measured['doc']['width'] <= 390, measured
        assert measured['chat']['bottom'] <= 845, measured
        page.screenshot(path=str(OUTPUT / 'mobile.png'))
        results['mobile_tabs_preserve_draft'] = measured

        for scenario, label in [('emagstatus=empty', '还没有店铺资料'), ('wbcase=offline', '暂时无法读取')]:
            visit(page, query=scenario)
            page.get_by_text(label, exact=True).wait_for()
        results['empty_and_error_states'] = True
        visit(page, query='agentdown=1')
        page.locator('.sw-chat-body textarea').wait_for()
        page.get_by_role('button', name='让 AI 分析').first.click()
        page.locator('.sw-chat-body .cc-send').click()
        page.wait_for_function('window.__lastFallbackChatBody?.messages')
        fallback = page.evaluate('window.__lastFallbackChatBody.messages[0].content')
        assert 'demo-ro' in fallback and 'demo-v1' in fallback
        page.get_by_text('兜底通道答的这一段。', exact=False).first.wait_for()
        results['fallback_retains_store_scope'] = True

        visit(page, width=1366, height=768)
        page.locator('.sw-workbench').evaluate("element => element.style.zoom = '1.5'")
        assert page.locator('.sw-chat-body textarea').is_visible()
        assert page.get_by_role('button', name='历史', exact=True).is_visible()
        assert page.locator('.sw-suggestion-list').evaluate('element => element.clientHeight > 40')
        page.screenshot(path=str(OUTPUT / 'zoom.png'))
        results['zoom_controls_accessible'] = True
        page.goto(f'{BASE}/?r=/')
        page.wait_for_url('**/workbench')
        page.get_by_role('heading', name='店铺工作台', exact=True).wait_for()
        results['default_landing'] = True
        assert not errors, errors
        browser.close()
    (OUTPUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=True))


if __name__ == '__main__':
    main()
