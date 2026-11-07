import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parseResearchCsv} from '../src/pages/workbench/research/data.mjs';
test('CSV preserves quoted commas, newlines, explicit zero and rejects duplicate headers',()=>{
 assert.deepEqual(parseResearchCsv('pnk,name,price\r\nABC,"A, B",0\r\nDEF,"line\none",\r\n'),[{pnk:'ABC',name:'A, B',price:'0'},{pnk:'DEF',name:'line\none',price:''}]);
 assert.throws(()=>parseResearchCsv('pnk,pnk\na,b'),/header/i);
 assert.throws(()=>parseResearchCsv('pnk,name\n"unclosed,a'),/quote/i);
 assert.throws(()=>parseResearchCsv('pnk,name\na,b,c'),/column/i);
});
test('research catalogs have exact key parity',async()=>{
 const root=new URL('../src/pages/workbench/research/',import.meta.url);
 const en=JSON.parse(await readFile(new URL('en.json',root)));
 const zh=JSON.parse(await readFile(new URL('zh-CN.json',root)));
 assert.deepEqual(Object.keys(en).sort(),Object.keys(zh).sort());
 assert.ok(Object.values(en).every(v=>typeof v==='string'&&v.length));
});
