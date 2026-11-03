"""Regress store scope isolation after attachments and failed history restoration."""
import base64
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    results = {}
    with sync_playwright() as playwright:
        edge = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe'
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        for scenario in ('attachments', 'failed_history', 'pending_queue'):
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            context.add_init_script("localStorage.setItem('store-ops.workbench.history.admin', JSON.stringify([{storeId:'second-ro',snapshotId:'second-old',capturedAt:'2026-10-01',sessionId:'fail-b'}]))")
            if scenario == 'pending_queue':
                context.add_init_script("localStorage.setItem('ivyea-ops.console.queue:new', JSON.stringify([{text:'Other store pending evidence',state:'queued'}]))")
            page = context.new_page()
            page.goto('http://127.0.0.1:5202/?r=/workbench&wbcase=multi')
            editor = page.locator('.sw-chat-body textarea')
            editor.wait_for()
            if scenario == 'pending_queue':
                page.wait_for_timeout(500)
                results[scenario] = page.evaluate('window.__lastChatBody === undefined')
                context.close()
                continue
            if scenario == 'attachments':
                page.locator('.sw-chat-body input[type=file]').set_input_files({'name': 'store-a.png', 'mimeType': 'image/png', 'buffer': base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+kZz8AAAAASUVORK5CYII=')})
                page.locator('.sw-chat-body .cc-composer img[src^="data:"]').wait_for()
            else:
                editor.fill('Store A conversation')
                page.locator('.sw-chat-body .cc-send').click()
                page.locator('.sw-chat-body .cc-stop-secondary').wait_for()
                page.locator('.sw-chat-body .cc-stop-secondary').click()
                page.wait_for_function("!document.querySelector('.sw-chat-actions button').disabled")
            page.get_by_label('工作台店铺', exact=True).select_option('second-ro')
            page.get_by_text('Second store item', exact=True).wait_for()
            if scenario == 'attachments':
                page.get_by_role('button', name='为 second-ro 新建对话').click()
                page.wait_for_function("document.querySelector('.sw-chat-scope').textContent.includes('second-ro')")
                count = page.locator('.sw-chat-body .cc-composer img[src^="data:"]').count()
                results[scenario] = count == 0
            else:
                page.get_by_role('button', name='历史', exact=True).click()
                page.locator('.sw-history button').filter(has_text='fail-b').click()
                page.get_by_text('Synthetic history unavailable', exact=True).or_(page.locator('.sw-chat-history-error')).wait_for()
                if not editor.count():
                    results[scenario] = False
                    context.close()
                    continue
                editor.fill('Continue only store B')
                page.locator('.sw-chat-body .cc-send').click()
                page.wait_for_function("window.__lastChatBody?.message === 'Continue only store B'")
                payload = page.evaluate('window.__lastChatBody')
                results[scenario] = payload.get('session_id') != 's-live' and 'second-ro' in payload['system']
            context.close()
        browser.close()
    print(json.dumps(results))
    assert all(results.values()), results


if __name__ == '__main__':
    main()
