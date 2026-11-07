// Synthetic HTTP boundary for the real App research UI.
const rows:Record<string,any[]>={};
export function researchReply(path:string,method:string|undefined,body:unknown,scenario:string|null){
 const match=path.match(/^\/emag\/stores\/([^/]+)\/research(\/import)?$/);if(!match)return null;
 const history=rows[match[1]] ||= [];
 if(method==='post'){
  if(scenario==='conflict')throw Object.assign(new Error('Snapshot changed; reload first'),{response:{status:409,data:{detail:'Snapshot changed; reload first'}}});
  if(scenario==='invalid')throw Object.assign(new Error('Invalid source URL'),{response:{status:422,data:{detail:'Invalid source URL'}}});
  const data=typeof body==='string'?JSON.parse(body):body as any;
  const add=(payload:any)=>{const row={record_id:data.record_id||'record-'+(history.length+1),revision:(data.revision||0)+1,snapshot_id:'demo-v1',payload,actor:'harness',created_at:new Date().toISOString(),stale:false,match:{status:'matched',product_ids:['1']}};history.unshift(row);return row;};
  return match[2]?{records:data.rows.map(add)}:add(data.payload);
 }
 const seen=new Set();return {snapshot_id:'demo-v1',records:history.filter(r=>{if(seen.has(r.record_id))return false;seen.add(r.record_id);return true;}),history,truncated:false,comparisons:[],prompts:[],marketplace_writes:false};
}
