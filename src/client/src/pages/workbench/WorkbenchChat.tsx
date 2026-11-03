import { useEffect, useRef, useState } from 'react';
import Console from './Console';
import { ivyeaAgentStatus } from '../../api/ivyeaAgent';
import { useAuth } from '../../App';
import { validBinding, workbenchContext } from './simpleWorkbenchData.mjs';

export type WorkbenchChatProps = {
  data: any | null; store: string;
  promptDraft?: { id: number; text: string; storeId: string };
  onBusyChange: (busy: boolean) => void;
  onScopeChange: (store: string) => void;
};
type Scope = { storeId: string; snapshotId: string; capturedAt: string; context: string };
type History = { storeId: string; snapshotId: string; capturedAt: string; sessionId: string };

export default function WorkbenchChat({ data, store, promptDraft, onBusyChange, onScopeChange }: WorkbenchChatProps) {
  const { username } = useAuth();
  const historyKey = `store-ops.workbench.history.${username}`;
  const [scope, setScope] = useState<Scope | null>(null);
  const [session, setSession] = useState('');
  const [revision, setRevision] = useState(0);
  const [draftCutoff, setDraftCutoff] = useState(0);
  const [historyError, setHistoryError] = useState('');
  const [busy, setBusy] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<History[]>([]);
  const [status, setStatus] = useState('正在连接…');
  const busyRef = useRef(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(historyKey) || '[]');
      if (Array.isArray(saved)) setHistory(saved.filter(item => validBinding(item, typeof item?.storeId === 'string' ? [item.storeId] : [])).slice(0, 20));
    } catch { setHistory([]); }
  }, [historyKey]);

  useEffect(() => {
    let alive = true;
    const check = () => ivyeaAgentStatus().then(result => {
      if (alive) setStatus(result.available ? '已连接' : '暂未连接，可在设置中检查');
    }).catch(() => { if (alive) setStatus('连接状态未知'); });
    void check();
    const timer = setInterval(check, 30000);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  useEffect(() => {
    if (!scope && data && data.store_id === store) {
      setScope({ storeId: store, snapshotId: data.snapshot_id, capturedAt: data.captured_at, context: workbenchContext(data) });
    }
  }, [data, store, scope]);
  useEffect(() => { onScopeChange(scope?.storeId || ''); }, [scope?.storeId, onScopeChange]);

  function notifyBusy(value: boolean) {
    busyRef.current = value;
    setBusy(value);
    onBusyChange(value);
  }
  function newConversation() {
    if (busyRef.current || !data || data.store_id !== store) return;
    setScope({ storeId: store, snapshotId: data.snapshot_id, capturedAt: data.captured_at, context: workbenchContext(data) });
    setSession(''); setRevision(value => value + 1); setHistoryOpen(false);
    setDraftCutoff(promptDraft?.id || 0); setHistoryError('');
  }
  function remember(id: string) {
    setSession(id);
    if (!id) {
      // Failed restoration must never retain a previous session or its composer evidence.
      setRevision(value => value + 1);
      setDraftCutoff(promptDraft?.id || 0);
      setHistoryError('无法打开这条历史对话。已清空旧对话视图，可重试历史或新建对话。');
      return;
    }
    if (!scope) return;
    const item = { storeId: scope.storeId, snapshotId: scope.snapshotId, capturedAt: scope.capturedAt, sessionId: id };
    setHistory(previous => {
      const next = [item, ...previous.filter(row => row.sessionId !== id)].slice(0, 20);
      try { localStorage.setItem(historyKey, JSON.stringify(next)); } catch { /* History is optional. */ }
      return next;
    });
  }
  function openHistory(item: History) {
    if (busyRef.current || !validBinding(item, [store])) return;
    setScope({ ...item, context: `当前会话仅属于店铺 ${item.storeId}，原始证据快照 ${item.snapshotId}，采集时间 ${item.capturedAt}。历史数据不是实时状态，继续分析前核实所需证据，不自动执行平台写入。` });
    setSession(item.sessionId); setHistoryOpen(false); setRevision(value => value + 1);
    setDraftCutoff(promptDraft?.id || 0); setHistoryError('');
  }
  const mismatch = !!scope && scope.storeId !== store;
  const scopedDraft = !mismatch && promptDraft && promptDraft.id > draftCutoff && promptDraft.storeId === scope?.storeId ? promptDraft : undefined;
  return <section className="sw-chat" aria-label="AI 店铺助手">
    <header className="sw-panel-head"><div><h2>店铺助手</h2></div><div className="sw-chat-actions">
      <button type="button" disabled={busy || !data} onClick={newConversation}>新对话</button>
      <button type="button" aria-expanded={historyOpen} disabled={busy} onClick={() => setHistoryOpen(value => !value)}>历史</button>
    </div></header>
    <div className="sw-chat-status">{status}</div>
    {scope && <div className="sw-chat-scope">对话店铺 <strong>{scope.storeId}</strong><details className="sw-chat-info"><summary>资料</summary><p>采集于 {scope.capturedAt}</p><p>{scope.snapshotId}</p></details></div>}
    {historyError && <div role="alert" className="sw-scope-warning sw-chat-history-error">{historyError}</div>}
    {mismatch && <div role="status" className="sw-scope-warning">当前对话仍属于 {scope?.storeId}。<button type="button" disabled={busy || !data} onClick={newConversation}>为 {store} 新建对话</button>{busy && <span>请先等待或停止当前任务。</span>}</div>}
    {historyOpen && <div className="sw-history" aria-label="本店历史对话"><h3>{store || '尚未选择店铺'} · 历史</h3>{history.filter(item => item.storeId === store).map(item => <button type="button" key={item.sessionId} onClick={() => openHistory(item)}>对话 {item.sessionId.slice(0, 14)}<small>{item.snapshotId} · {item.capturedAt}</small></button>)}{!history.some(item => item.storeId === store) && <p>此浏览器尚未记录本店对话。</p>}</div>}
    <div className="sw-chat-body">{scope ? <Console key={revision} embedded minimal sessionId={session} onSessionChange={remember} queueScope={JSON.stringify([username, scope.storeId])} contextText={scope.context} promptDraft={scopedDraft} onBusyChange={notifyBusy} /> : <div className="sw-chat-welcome"><h3>和 AI 一起查看店铺</h3><p>读取店铺资料后即可开始。对话将标注所属店铺与证据版本。</p></div>}</div>
  </section>;
}
