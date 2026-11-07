/** Drop blank optional inputs without converting explicit zero to missing. */
export function cleanPayload(value) {
  if (Array.isArray(value)) return value.map(cleanPayload);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([,v]) => !(typeof v === 'string' && !v.trim())).map(([k,v]) => [k,cleanPayload(v)]));
  return value;
}
export function safeEvidenceUrl(value) {
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password ? url.href : null; } catch { return null; }
}

/** Only the latest head response can establish a current assessment. */
export function mergeVerifiedHistory(head, older, cached) {
  const merged = new Map();
  for (const row of [...head, ...older.map(row => ({...row,current:false})), ...cached.map(row => ({...row,current:false}))]) {
    const key = row.record_id + ':' + row.revision;
    if (!merged.has(key)) merged.set(key,row);
  }
  return [...merged.values()];
}
