import {useEffect,useRef,useState} from 'react';
import {api} from '../../../api/client';
import {errText} from '../../../lib/errText';
import en from './en.json';
import zh from './zh-CN.json';
import './playbooks.css';
import {cleanPayload,safeEvidenceUrl,mergeVerifiedHistory} from './data.mjs';

type Kind='listing'|'variant'|'competitor'|'ads'|'inbound'|'cost_evidence';
type Payload=Record<string, any>;
type Product={product_id:string;name:string;sku:string;stock:number|null};
type Source={source_id?:string;id?:string;title:string;locator?:string;version?:string;date?:string;caveat?:string;review_status?:string};
type Saved={record_id:string;kind:Kind;product_id:string;snapshot_id:string;revision:number;payload:Payload;assessment:{checks:{key:string;status:string;source_ids:string[]}[];metrics:Record<string,unknown>;source_ids:string[]};actor:string;updated_at:string;stale:boolean;current:boolean;sequence:number};
type View={store_id:string;snapshot_id:string;captured_at:string;products:Product[];sources:Source[];repairs:{product_id:string;issue_id:string;reason:string;rule_ids:string[];source_ids:string[]}[];records:Saved[];records_next_before?:number|null};
const kinds:Kind[]=['listing','variant','competitor','ads','inbound','cost_evidence'];
const tri=['unknown','confirmed','failed'];
const fields:Record<Kind,string[]>={listing:['title','description','brand','model','color','size','package_contents','ean','source_language','content_language','evidence_url','category_access','commission_contract','mandatory_complete','title_matches','images_match','main_image_white','main_image_no_overlay','ean_matches','dimensions_confirmed'],variant:['family_name','family_id','family_type'],competitor:['url','observed_at','price_gross_ron','delivery','specification','comparable'],ads:['campaign_id','adset_id','campaign_status','adset_status','buy_button','listing_ready','balance_ron','budget_ron','impressions','clicks','spend_ron','orders','revenue_ron','period_start','period_end'],inbound:['reception_id','address_confirmed','box_count','tracking_number'],cost_evidence:['cost_field','value','unit','source_url','observed_at','valid_until','scope']};
const tristates=new Set(['category_access','commission_contract','mandatory_complete','title_matches','images_match','main_image_white','main_image_no_overlay','ean_matches','dimensions_confirmed','comparable','buy_button','listing_ready','address_confirmed']);
const choices:Record<string,string[]>={family_type:['color','size','other'],delivery:['unknown','emag_delivery','seller'],campaign_status:['unknown','draft','active','paused'],adset_status:['unknown','draft','active','paused'],unit:['CNY','RON','percent','RON_per_CNY'],cost_field:['purchase_cny','cny_to_ron','domestic_cny','international_ron','duties_ron','fulfilment_ron','other_ron','commission_pct','vat_pct','return_allowance_ron']};
export default function PlaybooksPanel({store,snapshotId}:{store:string;snapshotId:string}){
 const [locale,setLocale]=useState<'en'|'zh-CN'>(()=>{try{return localStorage.getItem('emag.playbooks.locale')==='zh-CN'?'zh-CN':'en';}catch{return 'en';}});
 const catalog:Record<string,string>=locale==='en'?en:zh;const t=(key:string)=>catalog[key]||en[key as keyof typeof en]||catalog.checkFallback;
 const [view,setView]=useState<View|null>(null),[product,setProduct]=useState(''),[kind,setKind]=useState<Kind>('listing'),[payload,setPayload]=useState<Payload>({}),[editing,setEditing]=useState<Saved|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const generation=useRef(0);const selection=useRef(0);
 function reset(){selection.current++;setPayload({});setEditing(null);setError('');setMessage('');}
 async function load(){const epoch=++generation.current;setView(null);reset();setProduct('');setBusy(false);try{const r=await api.get(`/emag/stores/${encodeURIComponent(store)}/playbooks`);if(epoch!==generation.current)return;setView(r.data);setProduct(r.data.products[0]?.product_id||'');}catch(e){if(epoch===generation.current)setError(errText(e,t('loadError')));}}
 useEffect(()=>{void load();return()=>{generation.current++;selection.current++;};},[store,snapshotId]);
 const filtered=view?.records.filter(r=>r.product_id===product&&r.kind===kind)||[];

 function update(field:string,value:unknown){setPayload(p=>({...p,[field]:value}));}
 async function save(){if(!view||!view.products.some(p=>p.product_id===product)||busy)return;const epoch=generation.current,selected=selection.current;setBusy(true);setError('');setMessage('');try{await api.post(`/emag/stores/${encodeURIComponent(store)}/playbooks/records`,{snapshot_id:view.snapshot_id,kind,product_id:product,payload:cleanPayload(payload),record_id:editing?.record_id||null,revision:editing?.revision||0});if(epoch!==generation.current||selected!==selection.current)return;const r=await api.get(`/emag/stores/${encodeURIComponent(store)}/playbooks`);if(epoch===generation.current&&selected===selection.current){setView(r.data);setEditing(null);setPayload({});setMessage(t('saved'));}}catch(e){if(epoch===generation.current&&selected===selection.current)setError(errText(e,t('saveError')));}finally{if(epoch===generation.current)setBusy(false);}}
 async function older(){
  if(!view?.records_next_before||busy)return;
  const epoch=generation.current;setBusy(true);setError('');
  try{
   const r=await api.get(`/emag/stores/${encodeURIComponent(store)}/playbooks`,{params:{before_sequence:view.records_next_before}});
   if(epoch!==generation.current)return;
   const head=await api.get(`/emag/stores/${encodeURIComponent(store)}/playbooks`);
   if(epoch!==generation.current)return;
   if(r.data.snapshot_id!==view.snapshot_id||head.data.snapshot_id!==view.snapshot_id){setView(null);setProduct('');selection.current++;setPayload({});setEditing(null);setError(t('snapshotChanged'));return;}
   // Current flags from a prior page cannot certify a later ledger generation.
   setView(previous=>({...head.data,records_next_before:r.data.records_next_before,
    records:mergeVerifiedHistory(head.data.records,r.data.records,previous?.records||[])}));
  }catch(e){if(epoch===generation.current)setError(errText(e,t('loadError')));}finally{if(epoch===generation.current)setBusy(false);}
 }

 function control(field:string,value:any,onChange:(v:string)=>void,id:string){const options=tristates.has(field)?tri:choices[field];return <label key={id} style={{display:'grid',gap:4,minWidth:0}}>{t('field.'+field)}{options?<select aria-label={t('field.'+field)} value={value??(tristates.has(field)?'unknown':'')} onChange={e=>onChange(e.target.value)}>{!tristates.has(field)&&<option value="">{t('unknown')}</option>}{options.map(o=><option key={o} value={o}>{catalog[o]||catalog['option.'+o]||o}</option>)}</select>:['description','package_contents','specification','scope','note'].includes(field)?<textarea aria-label={t('field.'+field)} rows={field==='description'?5:2} maxLength={field==='description'?40000:2000} value={value??''} onChange={e=>onChange(e.target.value)}/>:<input aria-label={t('field.'+field)} value={value??''} maxLength={2000} onChange={e=>onChange(e.target.value)}/>}</label>;}
 function refs(ids:string[]){return ids.map(id=>{const s=view?.sources.find(x=>(x.source_id||x.id)===id);return <details key={id}><summary>{s?.title||id}</summary><p>{s?.locator} · {s?.version} · {s?.date}</p><p>{s?.caveat}</p><p>{t('review')}</p></details>;});}
 return <section className="emag-playbooks" data-testid="playbooks-panel" style={{border:'1px solid var(--border)',padding:20,marginTop:20,minWidth:0}} lang={locale}>
 <h2>{t('heading')}</h2><label>{t('language')} <select aria-label={t('language')} value={locale} onChange={e=>{const l=e.target.value as 'en'|'zh-CN';setLocale(l);try{localStorage.setItem('emag.playbooks.locale',l);}catch{}}}><option value="en">{t('english')}</option><option value="zh-CN">{t('chinese')}</option></select></label><p>{t('manual')}</p>
 <button className="tbtn" disabled={busy} onClick={()=>void load()}>{t('reload')}</button>{error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
 {!view&&!error&&<p>{t('loading')}</p>}{view&&<><p>{t('current')}: {view.snapshot_id} · {new Date(view.captured_at).toLocaleString(locale,{timeZone:'Europe/Bucharest'})}</p>
 <label>{t('product')} <select aria-label={t('product')} disabled={busy} value={product} onChange={e=>{reset();setProduct(e.target.value);}}>{view.products.map(p=><option key={p.product_id} value={p.product_id}>{p.name||p.product_id} · {p.sku}</option>)}{[...new Set(view.records.map(r=>r.product_id))].filter(id=>!view.products.some(p=>p.product_id===id)).map(id=><option key={id} value={id}>{id} · {t('archivedProduct')}</option>)}</select></label><p>{t('stock')}: {view.products.find(p=>p.product_id===product)?.stock??t('unknown')}</p>
 <h3>{t('repairs')}</h3>{view.repairs.filter(r=>r.product_id===product).length?view.repairs.filter(r=>r.product_id===product).map(r=><article key={r.issue_id}><p>{t('repair.'+r.reason)} · {r.issue_id}</p><ul>{r.rule_ids.map(rule=><li key={rule}>{t('rule.'+rule)}</li>)}</ul>{refs(r.source_ids)}</article>):<p>{t('noRepairs')}</p>}
 <label>{t('kind')} <select aria-label={t('kind')} disabled={busy} value={kind} onChange={e=>{reset();setKind(e.target.value as Kind);}}>{kinds.map(k=><option key={k} value={k}>{t('kind.'+k)}</option>)}</select></label>
 <p>{t(kind==='cost_evidence'?'costHelp':kind+'Help')}</p><p>{t('dateHelp')}</p><form onSubmit={e=>{e.preventDefault();void save();}}><fieldset disabled={busy||!view.products.some(p=>p.product_id===product)} style={{border:0,padding:0,minWidth:0}}><div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,250px),1fr))',gap:12}}>{fields[kind].map(f=>control(f,payload[f],v=>update(f,v),f))}</div>
 {(kind==='variant'||kind==='inbound')&&(()=>{const key=kind==='variant'?'members':'items';const rows:Payload[]=payload[key]||[];return <section><h4>{t(key)}</h4>{rows.map((row,index)=><div key={index} style={{display:'flex',gap:10,flexWrap:'wrap',padding:'10px 0'}}><label>{t('product')}<select aria-label={`${t('product')} ${index+1}`} value={row.product_id||''} onChange={e=>update(key,rows.map((r,i)=>i===index?{...r,product_id:e.target.value}:r))}><option value="">{t('unknown')}</option>{view.products.map(p=><option key={p.product_id} value={p.product_id}>{p.name||p.product_id}</option>)}</select></label>{(kind==='variant'?['value']:['ean','expected_ean','quantity','box']).map(f=>control(f,row[f],v=>update(key,rows.map((r,i)=>i===index?{...r,[f]:v}:r)),key+index+f))}<button type="button" className="tbtn" onClick={()=>update(key,rows.filter((_,i)=>i!==index))}>{t('remove')}</button></div>)}<button type="button" className="tbtn" disabled={rows.length>=100} onClick={()=>update(key,[...rows,{}])}>{t('add')}</button></section>;})()}
 {control('note',payload.note,v=>update('note',v),'note')}<button className="tbtn" type="submit">{busy?t('saving'):t('save')}</button><button className="tbtn" type="button" onClick={reset}>{t('new')}</button>{editing&&<p>{t('revision')} {editing.revision} · {editing.record_id}</p>}</fieldset></form>
 <h3>{t('history')}</h3>{!filtered.length&&<p>{t('empty')}</p>}{filtered.map(r=><details key={r.record_id+':'+r.revision}><summary>{t('revision')} {r.revision} · {r.stale?t('stale'):r.current?t('current'):t('superseded')} · {new Date(r.updated_at).toLocaleString(locale,{timeZone:'Europe/Bucharest'})}</summary><p>{t('actor')}: {r.actor}</p><p>{r.snapshot_id}</p>{(r.stale||!r.current)?<p>{t(r.stale?'stale':'superseded')}</p>:<><h4>{t('checks')}</h4><ul>{r.assessment.checks.map(c=><li key={c.key}>{t('check.'+c.key)}: {t(c.status)}{refs(c.source_ids)}</li>)}</ul><dl>{Object.entries(r.assessment.metrics||{}).map(([key,value])=><div key={key}><dt>{t('metric.'+key)}</dt><dd>{value==null?t('unknown'):String(value)}</dd></div>)}</dl></>}
 <dl>{Object.entries(r.payload).map(([key,value])=><div key={key}><dt>{t('field.'+key)}</dt><dd style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{typeof value==='string'?(()=>{const url=safeEvidenceUrl(value);return url?<a href={url} target="_blank" rel="noopener noreferrer">{value}</a>:value;})():JSON.stringify(value)}</dd></div>)}</dl>{refs(r.assessment.source_ids||[])}<button className="tbtn" disabled={busy} onClick={()=>{reset();setPayload(structuredClone(r.payload));setEditing(r.stale||!r.current?null:r);}}>{r.stale||!r.current?t('new'):t('edit')}</button></details>)}
 {view.records_next_before&&<button className="tbtn" disabled={busy} onClick={()=>void older()}>{t('older')}</button>}
 <h3>{t('sources')}</h3>{refs(view.sources.map(s=>s.source_id||s.id||''))}</>}
 </section>;
}
