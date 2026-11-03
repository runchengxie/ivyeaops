import { dashboardMetrics } from './emagDashboardData.mjs';

const known = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
const reasons = { invalid_price: '价格无效', documentation_rejected: '资料被拒', blocked: '平台受阻' };

/** Derive a bounded work queue from observations, never a forecast or write plan. */
export function workbenchSuggestions(data) {
  const rows = new Map();
  for (const offer of data.offers || []) {
    rows.set(String(offer.id), { offerId: String(offer.id), name: offer.name || String(offer.id), sku: offer.part_number || '', stock: known(offer.general_stock), issues: [], aged: null });
  }
  for (const row of data.clearance?.rows || []) {
    const id = String(row.offer_id);
    const previous = rows.get(id) || { offerId: id, name: row.name || id, sku: row.sku || '' };
    rows.set(id, { ...previous, stock: known(row.stock), issues: row.issues || [], aged: row.aging_status === 'consistent' ? known(row.aged_181_plus) : null });
  }
  for (const issue of data.issues || []) {
    const id = String(issue.id);
    const row = rows.get(id) || { offerId: id, name: id, sku: '', stock: known(issue.general_stock), issues: [], aged: null };
    if (!row.issues.some(existing => existing.issue_id === issue.issue_id)) row.issues = [...row.issues, issue];
    rows.set(id, row);
  }
  const result = [];
  for (const row of rows.values()) {
    const blocker = row.issues.find(issue => reasons[issue.reason]);
    const base = { offerId: row.offerId, name: row.name, sku: row.sku, stock: row.stock, issueId: blocker?.issue_id || '' };
    if (blocker && row.stock > 0) result.push({ ...base, kind: 'restore', rank: 0, reason: reasons[blocker.reason], action: '先核对平台原因，恢复可售状态' });
    else if (row.stock > 0 && row.aged > 0) result.push({ ...base, kind: 'aging', rank: 1, reason: `已核对超过180天库存 ${row.aged} 件`, action: '核对历史成本与持有费用，拟库存消化方案' });
    else if (row.stock === null || blocker) result.push({ ...base, kind: 'verify', rank: 2, reason: blocker ? reasons[blocker.reason] : '库存尚未核实', action: '先补齐库存与平台状态证据' });
    else if (row.stock > 0) result.push({ ...base, kind: 'stock', rank: 3, reason: `已知库存 ${row.stock} 件`, action: '复查已有库存，安排后续消化' });
  }
  return result.sort((a, b) => a.rank - b.rank || (b.stock ?? -1) - (a.stock ?? -1) || a.offerId.localeCompare(b.offerId)).slice(0, 5);
}

export function workbenchContext(data) {
  const metrics = dashboardMetrics(data);
  return [
    '当前对话的店铺证据范围（仅作观察，不自动执行平台操作）：',
    `店铺：${data.store_id}；快照：${data.snapshot_id}；采集时间：${data.captured_at}。`,
    `商品记录 ${metrics.offers}；窗口内订单观察 ${metrics.orders ?? '未知'}；已知库存小计 ${metrics.stock ?? '未知'}；异常观察 ${metrics.issueCount}。`,
    '以上是已采集快照，不是实时数据；未知字段不等于零，订单观察不等于已成交或回款，成本及利润未核实。',
    '只分析该店铺和明确的快照/商品引用，不能将其他店铺或对话的材料当作本店证据。需要最新资料时先核实来源，给建议与理由，不自动改价。',
  ].join('\n');
}

export function suggestionPrompt(data, item) {
  return `「${item.name}」${item.reason}，应该先怎么处理？
店铺 ${data.store_id} · 商品 ${item.offerId} / ${item.sku || 'SKU 未采集'} · 库存 ${item.stock ?? '未知'}。
请根据资料 ${data.snapshot_id}（${data.captured_at}）、问题 ${item.issueId || '暂无独立引用'} 核对原因并给出下一步建议，先不执行操作。`;
}

/** Local history stores only explicit session/scope references, never evidence bodies. */
export function validBinding(value, stores) {
  return !!value && typeof value.storeId === 'string' && stores.includes(value.storeId)
    && typeof value.sessionId === 'string' && !!value.sessionId && value.sessionId.length <= 200
    && typeof value.snapshotId === 'string' && typeof value.capturedAt === 'string';
}
