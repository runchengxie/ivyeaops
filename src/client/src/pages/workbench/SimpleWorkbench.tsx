import { Suspense, useEffect, useMemo, useRef, useState, type ComponentType } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, RefreshCw, SlidersHorizontal, Store, MessageSquare, ArrowRight, Package, ShoppingBag, Layers, CircleAlert } from 'lucide-react';
import { api } from '../../api/client';
import { catalogSections } from '../../lib/navRegistry';
import { errText } from '../../lib/errText';
import { dashboardMetrics } from './emagDashboardData.mjs';
import { suggestionPrompt, workbenchSuggestions } from './simpleWorkbenchData.mjs';
import type { WorkbenchChatProps } from './WorkbenchChat';
import './simple-workbench.css';

type Tab = 'overview' | 'suggestions' | 'chat';

export default function SimpleWorkbench({ demo = false, ChatComponent, viewer, onSettings, onLogout }: {
  demo?: boolean; ChatComponent: ComponentType<WorkbenchChatProps>;
  viewer?: { role: string; permissions: string[]; username: string };
  onSettings?: () => void; onLogout?: () => void;
}) {
  const { role, permissions, username } = viewer || { role: 'user', permissions: [], username: '' };
  const [query] = useSearchParams();
  const [stores, setStores] = useState<{ store_id: string }[]>([]);
  const [store, setStore] = useState(query.get('store') || '');
  const [snapshot, setData] = useState<any>(null);
  const data = snapshot?.store_id === store ? snapshot : null;
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [tab, setTab] = useState<Tab>('overview');
  const [chatBusy, setChatBusy] = useState(false);
  const [chatScope, setChatScope] = useState('');
  const [draft, setDraft] = useState<WorkbenchChatProps['promptDraft']>();
  const draftId = useRef(0);
  const generation = useRef(0);
  const tools = useMemo(() => catalogSections({ isAdmin: demo || role === 'admin', permissions }).flatMap(group => group.items)
    .filter(item => item.to !== '/workbench' && (!demo || ['/dashboard', '/emag', '/market', '/playbook', '/listing', '/tools'].includes(item.to))), [demo, role, permissions]);
  const Chat = ChatComponent;

  useEffect(() => {
    let alive = true;
    setError(''); setLoading(true);
    api.get('/emag/stores').then(response => {
      if (!alive) return;
      const items = Array.isArray(response.data) ? response.data.filter(item => typeof item?.store_id === 'string') : [];
      setStores(items);
      setStore(previous => previous && items.some(item => item.store_id === previous) ? previous : items[0]?.store_id || '');
      if (!items.length) setLoading(false);
    }).catch(error => { if (alive) { setError(errText(error, '无法读取店铺，请检查权限和连接。')); setLoading(false); } });
    return () => { alive = false; };
  }, [refresh]);
  useEffect(() => {
    const version = ++generation.current;
    if (!store) return;
    setData(null); setError(''); setLoading(true); setDraft(undefined);
    const controller = new AbortController();
    api.get(`/emag/stores/${encodeURIComponent(store)}/workspace`, { signal: controller.signal }).then(response => {
      if (version !== generation.current) return;
      if (response.data?.store_id !== store || !Array.isArray(response.data?.offers) || !Array.isArray(response.data?.issues)) throw new Error('店铺资料不完整，请重新采集。');
      setData(response.data);
    }).catch(error => { if (!controller.signal.aborted && version === generation.current) setError(errText(error, '无法读取店铺快照，请检查连接或先完成采集。')); }).finally(() => { if (version === generation.current) setLoading(false); });
    return () => { generation.current++; controller.abort(); };
  }, [store, refresh]);
  const metrics = data ? dashboardMetrics(data) : null;
  const suggestions = data ? workbenchSuggestions(data) : [];
  const metricItems = [
    { name: '商品记录', value: metrics?.offers, unit: '条', icon: Package },
    { name: '窗口内订单', value: metrics?.orders, unit: '单', icon: ShoppingBag },
    { name: '已知库存', value: metrics?.stock, unit: '件', icon: Layers },
    { name: '异常观察', value: metrics?.issueCount, unit: '项', icon: CircleAlert },
  ];
  function analyze(item: ReturnType<typeof workbenchSuggestions>[number]) {
    if (!data || chatBusy || chatScope !== store) return;
    setDraft({ id: ++draftId.current, text: suggestionPrompt(data, item), storeId: store });
    setTab('chat');
  }
  return <main className="sw-workbench" data-mobile-tab={tab} aria-label="店铺工作台">
    <header className="sw-header"><div className="sw-brand"><span className="sw-brand-mark"><Store size={20} /></span><div><h1>店铺工作台</h1><span>eMAG RO <span className="sw-header-separator">/</span> 先看清，再调整</span></div></div>
      <div className="sw-header-controls"><label className="sw-store-select"><span>店铺</span><select aria-label="工作台店铺" value={store} onChange={event => setStore(event.target.value)} disabled={!stores.length}>{stores.map(item => <option key={item.store_id}>{item.store_id}</option>)}</select></label>
        <button type="button" className="sw-icon-button" aria-label="刷新店铺资料" disabled={loading || !store} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={17} /></button>
        <details className="sw-more"><summary><SlidersHorizontal size={16} /><span>更多</span></summary><nav aria-label="更多工具">{tools.map(item => <Link key={item.to} to={item.to}>{item.label}<ArrowUpRight size={13} /></Link>)}{demo ? <><a href="../zh-CN/index.html">使用文档</a><button type="button" onClick={() => location.reload()}>重置演示</button></> : <><button type="button" onClick={onSettings}>设置</button><button type="button" onClick={onLogout}>退出 {username}</button></>}</nav></details>
      </div>
    </header>
    {demo && <div className="sw-demo-notice" role="status">模拟演示 · 虚构数据与演示回复，刷新重置，不连接真实店铺或 AI 服务</div>}
    <nav className="sw-mobile-tabs" aria-label="工作台视图">{([['overview', '概况'], ['suggestions', '建议'], ['chat', '对话']] as const).map(([value, label]) => <button key={value} type="button" aria-pressed={tab === value} onClick={() => setTab(value)}>{label}</button>)}</nav>
    <div className="sw-body">
      <div className="sw-left">
        <section className="sw-overview" aria-label="店铺概况"><header className="sw-section-heading"><div><span className="sw-eyebrow">STORE OVERVIEW</span><h2>店铺概况</h2></div><span className="sw-evidence-badge">{loading ? '读取中' : data ? '已采集快照' : '暂无资料'}</span></header>
          <div className="sw-metrics">{metricItems.map(({ name, value, unit, icon: MetricIcon }) => <div className="sw-metric" key={name}><div><MetricIcon size={16} /><span>{name}</span></div><strong>{loading ? '—' : value ?? '未知'}<small>{value == null || loading ? '' : unit}</small></strong></div>)}</div>
          <div className="sw-evidence-line">{data ? <>采集于 <time dateTime={data.captured_at}>{new Date(data.captured_at).toLocaleString()}</time><span title={data.snapshot_id}> · {data.snapshot_id}</span></> : loading ? '正在读取店铺资料…' : '尚无可用快照'}</div>
          <p className="sw-note">已知库存不含未知部分；订单为采集窗口内的观察，非成交额或回款。</p>
          {data && <details className="sw-evidence-details"><summary>来源与数据范围</summary><p>{data.source} · {data.snapshot_id}</p><p>库存未知 {metrics?.stockUnknown ?? '未核实'} 条 · 价格状态未知 {metrics?.priceUnknown ?? '未核实'} 条</p>{data.commercial_summary?.window && <p>订单窗口：{data.commercial_summary.window.start} — {data.commercial_summary.window.end}</p>}<ul>{(data.limitations || []).map((line: string, index: number) => <li key={index}>{line}</li>)}</ul></details>}
          {error && <div className="sw-state" role="alert"><strong>暂时无法读取</strong><p>{error}</p><button type="button" onClick={() => setRefresh(value => value + 1)}>重试</button></div>}
          {!loading && !error && !stores.length && <div className="sw-state"><strong>还没有店铺资料</strong><p>完成店铺连接与首次采集后，这里会显示概况。</p>{!demo && <button type="button" onClick={onSettings}>打开设置</button>}</div>}
        </section>
        <section className="sw-suggestions" aria-label="优先调整建议"><header className="sw-section-heading"><div><span className="sw-eyebrow">NEXT ACTIONS</span><h2>优先调整</h2></div><Link to={`/emag?store=${encodeURIComponent(store)}`}>全部明细 <ArrowUpRight size={14} /></Link></header><p className="sw-note">先恢复可售，再核查老库存。建议以当前证据为依据。</p>
          <div className="sw-suggestion-list">{suggestions.map((item, index) => <article className="sw-suggestion" key={item.offerId}><span className={`sw-priority sw-priority-${item.kind}`}>{String(index + 1).padStart(2, '0')}</span><div className="sw-suggestion-content"><div className="sw-suggestion-title"><h3>{item.name}</h3><span>{item.reason}</span></div><p>{item.action}</p><small>{item.sku || item.offerId} · 库存 {item.stock ?? '未知'}</small><div className="sw-suggestion-actions"><button type="button" disabled={chatBusy || chatScope !== store} onClick={() => analyze(item)}><MessageSquare size={13} />让 AI 分析</button><Link to={`/emag?store=${encodeURIComponent(store)}${item.issueId ? `&issue=${encodeURIComponent(item.issueId)}` : ''}`}>查看详情 <ArrowRight size={13} /></Link></div></div></article>)}{!suggestions.length && <div className="sw-state"><strong>{loading ? '正在整理建议…' : data ? '当前没有待展示的优先事项' : '等待店铺资料'}</strong><p>{data ? '未观察到异常不代表所有风险已排除，可继续与助手核对。' : '建议会随已采集的证据显示在这里。'}</p></div>}</div>
          <footer className="sw-suggestions-footer">{data ? `展示 ${suggestions.length} 项优先核查方向 · 不自动执行改价` : '只展示有来源的观察与建议'}</footer>
        </section>
      </div>
      <div className="sw-right"><Suspense fallback={<div className="sw-state">正在准备店铺助手…</div>}><Chat data={data} store={store} promptDraft={draft} onBusyChange={setChatBusy} onScopeChange={setChatScope} /></Suspense></div>
    </div>
  </main>;
}
