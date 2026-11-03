import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { execFileSync } from 'node:child_process';

async function load(path) {
  let source = process.env.UPSTREAM_BASELINE && /errText|useVersionCheck/.test(path)
    ? execFileSync('git', ['show', `main:src/client/${path.replace('../', '')}`], { encoding: 'utf8' })
    : readFileSync(new URL(path, import.meta.url), 'utf8');
  source = source.replace("import { useState, useEffect } from 'react';", 'const { useState, useEffect } = globalThis.versionHooks;');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
}

test('auth retries temporary failures and immediately rejects 401/403', async () => {
  const { checkAuth } = await load('../src/lib/checkAuth.ts');
  const delays = [];
  let calls = 0;
  assert.equal(await checkAuth(async () => { if (++calls < 3) throw Error('offline'); return 'user'; }, () => false, async n => delays.push(n)), 'user');
  assert.deepEqual(delays, [1000, 2000]);
  for (const status of [401, 403]) {
    calls = 0;
    await assert.rejects(checkAuth(async () => { calls++; throw { response: { status } }; }, () => false, async () => assert.fail('must not retry')));
    assert.equal(calls, 1);
  }
});

test('plugin error envelopes normalize strings, structured errors and validation arrays', async () => {
  const { errText } = await load('../src/lib/errText.ts');
  for (const data of [{ error: 'Unsupported' }, { error: { message: 'Unsupported' } }, { detail: [{ loc: ['body', 'url'], msg: 'Invalid URL' }] }]) {
    const text = errText({ response: { data } }, 'fallback');
    assert.equal(typeof text, 'string');
    assert.notEqual(text, 'fallback');
  }
});

test('disabled version hook schedules no network effects', async () => {
  const effects = [];
  globalThis.versionHooks = { useState: value => [value, () => {}], useEffect: fn => effects.push(fn) };
  const { useVersionCheck } = await load('../src/agents/hooks/useVersionCheck.ts');
  useVersionCheck('owner', 'repo', false);
  const originalFetch = globalThis.fetch;
  const originalInterval = globalThis.setInterval;
  try {
    globalThis.fetch = async () => assert.fail('disabled hook requested network');
    globalThis.setInterval = () => assert.fail('disabled hook scheduled polling');
    for (const effect of effects) assert.equal(effect(), undefined);
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.setInterval = originalInterval;
    delete globalThis.versionHooks;
  }
});

test('auth bounds retries and stops after cancellation', async () => {
  const { checkAuth } = await load('../src/lib/checkAuth.ts');
  let calls = 0;
  await assert.rejects(checkAuth(async () => { calls++; throw Error('offline'); }, () => false, async () => {}));
  assert.equal(calls, 5);
  let cancelled = false;
  calls = 0;
  await assert.rejects(checkAuth(async () => { calls++; throw Error('offline'); }, () => cancelled, async () => { cancelled = true; }));
  assert.equal(calls, 1);
});

test('download attaches anchor and preserves filename until deferred cleanup', async () => {
  const { saveBlob } = await load('../src/lib/saveBlob.ts');
  const events = [];
  const anchor = { style: {}, click() { events.push(['click', this.download]); }, remove() { events.push('remove'); } };
  const originals = { document: globalThis.document, setTimeout: globalThis.setTimeout, create: URL.createObjectURL, revoke: URL.revokeObjectURL };
  let cleanup;
  try {
    globalThis.document = { createElement: () => anchor, body: { appendChild: () => events.push('append') } };
    URL.createObjectURL = () => 'blob:test';
    URL.revokeObjectURL = url => events.push(['revoke', url]);
    globalThis.setTimeout = (fn, ms) => { cleanup = fn; assert.equal(ms, 60000); };
    saveBlob(new Blob(['report']), 'report.md');
    assert.deepEqual(events, ['append', ['click', 'report.md'], 'remove']);
    cleanup();
    assert.deepEqual(events.at(-1), ['revoke', 'blob:test']);
  } finally {
    globalThis.document = originals.document;
    globalThis.setTimeout = originals.setTimeout;
    URL.createObjectURL = originals.create;
    URL.revokeObjectURL = originals.revoke;
  }
});
