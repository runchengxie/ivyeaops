import assert from 'node:assert/strict';
import {mkdtemp,rm,writeFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {WsCDP,chromeArgs,evaluate,waitFor,delay} from './cdp.mjs';
const profile=await mkdtemp(path.join(os.tmpdir(),'emag-playbooks-ui-'));
const {cdp,chrome}=await WsCDP.launch(chromeArgs(profile));
try{
 const {targetId}=await cdp.send('Target.createTarget',{url:'about:blank'});
 const {sessionId}=await cdp.send('Target.attachToTarget',{targetId,flatten:true});
 const send=(method,params={})=>cdp.send(method,params,sessionId);
 await send('Runtime.enable');await send('Page.enable');
 const root='[data-testid="playbooks-panel"]';
 const text=()=>evaluate(send,`document.querySelector('${root}').innerText`);
 const change=async(label,value)=>evaluate(send,`(()=>{const e=document.querySelector('${root} [aria-label="${label}"]');const p=e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);
 const button=label=>evaluate(send,`[...document.querySelectorAll('${root} button')].find(e=>e.textContent===${JSON.stringify(label)}).click()`);
 async function open(scenario='normal'){await send('Page.navigate',{url:`http://127.0.0.1:5277/?r=/listing&pbcase=${scenario}`});await delay(500);await waitFor(send,`!!document.querySelector('${root} [aria-label="Title"]')`,'playbook form');}
 await open();assert.match(await text(),/Historical snapshot/);assert.match(await text(),/Compare cost evidence/);
 await change('Title','Synthetic saved title');await button('Save local record');await waitFor(send,`document.querySelector('${root}').innerText.includes('Local record saved.')`,'saved record');
 await evaluate(send,`[...document.querySelectorAll('${root} details')].find(e=>e.textContent.includes('Synthetic saved title')).open=true`);
 assert.match(await text(),/Synthetic saved title/);await button('Edit latest revision');await change('Title','Edited synthetic title');await button('Save local record');await waitFor(send,`document.querySelector('${root}').textContent.includes('Edited synthetic title')`,'edited revision');
 await change('Product','2');assert.equal(await evaluate(send,`document.querySelector('${root} [aria-label="Title"]').value`),'');assert.match(await text(),/Unknown/);await change('Product','1');
 for(const kind of ['variant','competitor','ads','inbound','cost_evidence']){await change('Workflow',kind);assert.ok(await evaluate(send,`!!document.querySelector('${root} form')`));}
 await change('Panel language','zh-CN');assert.match(await text(),/证据工作台/);await send('Page.reload');await delay(1000);await waitFor(send,`!!document.querySelector('${root} [aria-label="面板语言"]')`,'persisted Chinese');
 await change('面板语言','en');
 const computed=await evaluate(send,`(()=>{const e=document.querySelector('${root}');const c=getComputedStyle(e);return {display:c.display,width:e.getBoundingClientRect().width,overflow:c.overflowWrap};})()`);assert.ok(computed.width>250);assert.notEqual(computed.display,'none');
 await open('pages');await button('Load older revisions');await waitFor(send,`document.querySelectorAll('${root} > details').length>=2`,'older revisions');
 await open('revision-race');await button('Load older revisions');await waitFor(send,`document.querySelector('${root}').textContent.includes('New external revision')`,'refreshed current flags');
 await open('snapshot-race');await button('Load older revisions');await waitFor(send,`!!document.querySelector('${root} [role="alert"]')`,'snapshot pagination conflict');assert.equal(await evaluate(send,`!!document.querySelector('${root} form')`),false);assert.match(await text(),/snapshot changed/i);
 await open('validation');await change('Title','Rejected title');await button('Save local record');await waitFor(send,`!!document.querySelector('${root} [role="alert"]')`,'validation error');assert.match(await text(),/Period must end after/);
 await open('conflict');await change('Title','Conflicting title');await button('Save local record');await waitFor(send,`!!document.querySelector('${root} [role="alert"]')`,'revision conflict');assert.match(await text(),/Snapshot or revision changed/);
 await open();await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await delay(200);await writeFile('/tmp/emag-playbooks-desktop.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay(200);const mobile=await evaluate(send,`(()=>{const e=document.querySelector('${root}');const r=e.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,viewport:innerWidth,scroll:document.documentElement.scrollWidth};})()`);await writeFile('/tmp/emag-playbooks-mobile.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));assert.ok(mobile.right<=mobile.viewport+1,JSON.stringify(mobile));console.log('Mobile bounds',mobile);
 console.log('Real App playbooks: save, edit/history, six forms, stale caveat, bilingual persistence, 422/409, computed layout passed',computed);
}finally{cdp.ws.close();chrome.kill('SIGTERM');await new Promise(r=>chrome.once('exit',r));await rm(profile,{recursive:true,force:true,maxRetries:10,retryDelay:200});}
