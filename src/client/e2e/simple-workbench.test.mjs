import test from 'node:test';
import assert from 'node:assert/strict';
import { workbenchSuggestions, workbenchContext, suggestionPrompt, validBinding } from '../src/pages/workbench/simpleWorkbenchData.mjs';

const evidence = {
  store_id: 'store-a', snapshot_id: 'snapshot-a', captured_at: '2026-11-04T00:00:00Z', source: 'collected',
  offers: [{ id: 1, name: 'Blocked item', part_number: 'SKU-1', general_stock: 3 }, { id: 2, name: 'Old stock', general_stock: 9 }],
  summary: {}, issues: [{ id: 1, issue_id: 'issue-price', reason: 'invalid_price', general_stock: 3 }],
  clearance: { rows: [{ offer_id: '2', name: 'Old stock', stock: 9, aged_181_plus: 9, aging_status: 'consistent', issues: [] }] },
};

test('suggestions prioritize stocked blockers over verified old stock and retain exact references', () => {
  const result = workbenchSuggestions(evidence);
  assert.deepEqual(result.map(row => row.offerId), ['1', '2']);
  assert.equal(result[0].issueId, 'issue-price');
  assert.match(result[0].reason, /价格/);
  assert.match(result[1].reason, /180/);
});

test('unknown or invalid stocks never become positive stock or assumed aging', () => {
  const data = { ...evidence, issues: [], offers: [null, -1, '3', true].map((stock, i) => ({ id: i, general_stock: stock })),
    clearance: { rows: [{ offer_id: '0', stock: null, aged_181_plus: 8, aging_status: 'inconsistent', issues: [] }] } };
  const rows = workbenchSuggestions(data);
  assert.equal(rows.length, 4);
  assert.ok(rows.every(row => row.stock === null));
  assert.ok(rows.every(row => row.kind === 'verify'));
  assert.ok(rows.every(row => !row.reason.includes('180')));
});

test('suggestions are bounded, deduplicated and deterministic', () => {
  const data = { ...evidence, clearance: undefined, offers: Array.from({ length: 20 }, (_, id) => ({ id, general_stock: id + 1 })), issues: [] };
  assert.equal(workbenchSuggestions(data).length, 5);
  assert.deepEqual(workbenchSuggestions(data), workbenchSuggestions(data));
  assert.equal(new Set(workbenchSuggestions(evidence).map(row => row.offerId)).size, 2);
});

test('prompts carry store, snapshot and exact product/issue identity without invented values', () => {
  const context = workbenchContext(evidence);
  const prompt = suggestionPrompt(evidence, workbenchSuggestions(evidence)[0]);
  for (const text of [context, prompt]) {
    assert.ok(text.includes('store-a'));
    assert.ok(text.includes('snapshot-a'));
  }
  assert.ok(prompt.includes('SKU-1'));
  assert.ok(prompt.includes('issue-price'));
  assert.match(context, /采集/);
  assert.match(context, /未知|未核实/);
});

test('restored history bindings must belong to a known store and have valid references', () => {
  assert.equal(validBinding({ storeId: 'store-a', sessionId: 's1', snapshotId: 'old', capturedAt: 'then' }, ['store-a']), true);
  for (const value of [null, {}, { storeId: 'store-b', sessionId: 's1' }, { storeId: 'store-a', sessionId: {} }]) {
    assert.equal(validBinding(value, ['store-a']), false);
  }
});
