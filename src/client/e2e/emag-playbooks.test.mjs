import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import { cleanPayload, safeEvidenceUrl } from '../src/pages/workbench/playbooks/data.mjs';
const root='../src/pages/workbench/playbooks/';
test('blank optional metrics stay unknown and explicit zero survives',()=>{
 assert.deepEqual(cleanPayload({clicks:'0',spend_ron:'',note:'  ',items:[{quantity:'2',ean:''}]}),{clicks:'0',items:[{quantity:'2'}]});
});
test('evidence URLs reject executable schemes and credentials',()=>{
 assert.equal(safeEvidenceUrl('javascript:alert(1)'),null);
 assert.equal(safeEvidenceUrl('https://user:secret@example.com'),null);
 assert.equal(safeEvidenceUrl('https://example.com/evidence'),'https://example.com/evidence');
});
test('catalogs contain identical semantic keys with translated form fields',()=>{
 const en=JSON.parse(readFileSync(new URL(root+'en.json',import.meta.url)));
 const zh=JSON.parse(readFileSync(new URL(root+'zh-CN.json',import.meta.url)));
 assert.deepEqual(Object.keys(en).sort(),Object.keys(zh).sort());
 for(const key of ['field.title','field.budget_ron','field.expected_ean','stale','manual','kind.cost_evidence'])assert.ok(en[key]&&zh[key]);
});

test('older page current flags cannot survive a newer head revision', async()=>{
 const {mergeVerifiedHistory}=await import('../src/pages/workbench/playbooks/data.mjs');
 const old={record_id:'family',revision:1,current:true};
 const head={record_id:'family',revision:2,current:true};
 const merged=mergeVerifiedHistory([head],[old],[]);
 assert.equal(merged.find(r=>r.revision===1).current,false);
 assert.equal(merged.find(r=>r.revision===2).current,true);
 assert.equal(mergeVerifiedHistory([], [{record_id:'outside-head',revision:1,current:true}],[])[0].current,false);
});
