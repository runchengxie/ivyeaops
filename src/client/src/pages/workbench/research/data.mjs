/** Bounded RFC4180-style CSV import; server validates every field atomically. */
export function parseResearchCsv(text) {
 if(typeof text!=='string'||text.length>1000000)throw new Error('CSV exceeds size limit');
 const rows=[];let row=[],cell='',quoted=false,closed=false;
 const endCell=()=>{row.push(cell);cell='';closed=false;};
 const endRow=()=>{endCell();if(row.some(v=>v!==''))rows.push(row);row=[];};
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=c;continue;}
  if(c==='"'){if(cell||closed)throw new Error('Invalid CSV quote');quoted=true;}
  else if(c===',')endCell();
  else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;endRow();}
  else {if(closed)throw new Error('Unexpected character after quote');cell+=c;}
 }
 if(quoted)throw new Error('Unclosed CSV quote');
 if(cell||row.length||closed)endRow();
 if(rows.length<2||rows.length>501)throw new Error('CSV requires 1–500 data rows');
 const headers=rows.shift().map(v=>v.replace(/^\uFEFF/,'').trim());
 if(headers.some(h=>!h)||new Set(headers).size!==headers.length)throw new Error('Invalid CSV header');
 return rows.map(r=>{if(r.length!==headers.length)throw new Error('CSV column count mismatch');return Object.fromEntries(headers.map((h,i)=>[h,r[i]]));});
}
