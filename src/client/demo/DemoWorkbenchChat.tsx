import { useEffect, useRef, useState } from 'react';
import type { WorkbenchChatProps } from '../src/pages/workbench/WorkbenchChat';
import { demoReply } from './reply.mjs';

export default function DemoWorkbenchChat({ data, store, promptDraft, onBusyChange, onScopeChange }: WorkbenchChatProps) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [history, setHistory] = useState<typeof messages[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => { onScopeChange(store); }, [store, onScopeChange]);
  useEffect(() => { onBusyChange(busy); }, [busy, onBusyChange]);
  useEffect(() => { if (promptDraft) setText(promptDraft.text); }, [promptDraft]);
  useEffect(() => () => clearTimeout(timer.current), []);
  function send() {
    if (!text.trim() || !data || busy) return;
    setMessages(previous => [...previous, { role: 'user', text }]); setText(''); setBusy(true);
    timer.current = setTimeout(() => { setMessages(previous => [...previous, { role: 'assistant', text: demoReply(data) }]); setBusy(false); }, 900);
  }
  return <section className="sw-chat" aria-label="AI 店铺助手"><header className="sw-panel-head"><div><span className="sw-eyebrow">DEMO ASSISTANT</span><h2>店铺助手</h2></div><div className="sw-chat-actions"><button disabled={busy} onClick={() => { if (messages.length) setHistory(previous => [messages, ...previous]); setMessages([]); setText(''); setHistoryOpen(false); }}>新对话</button><button disabled={busy} onClick={() => setHistoryOpen(value => !value)}>历史</button></div></header>
    <div className="sw-chat-status"><span className="sw-status-dot" />模拟对话 · 不连接真实 AI 服务</div><div className="sw-chat-scope">演示店铺 <strong>{store || '等待资料'}</strong><span>{data?.snapshot_id}</span></div>
    <div className="sw-demo-thread" aria-live="polite">{!messages.length && <div className="sw-chat-welcome"><h3>今天先处理哪一项？</h3><p>点击左侧“让 AI 分析”，体验带入店铺与商品的对话。</p></div>}{messages.map((message, index) => <div className={`sw-demo-message sw-demo-${message.role}`} key={index}><small>{message.role === 'user' ? '你' : '店铺助手 · 演示回复'}</small><p>{message.text}</p></div>)}{busy && <p className="sw-note">正在准备演示回复…</p>}</div>
    <div className="sw-demo-composer"><textarea aria-label="演示对话输入" placeholder="问问店铺情况，或选择一项建议…" value={text} onChange={event => setText(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} /><div><span>演示回复，不调用模型</span>{busy ? <button onClick={() => { clearTimeout(timer.current); setBusy(false); setMessages(previous => [...previous, { role: 'assistant', text: '已停止演示回复。未调用模型或执行平台操作。' }]); }}>停止</button> : <button disabled={!text.trim() || !data} onClick={send}>发送 ↑</button>}</div></div>
    {historyOpen && <div className="sw-history"><h3>本次演示的历史对话</h3>{history.map((conversation, index) => <button key={index} onClick={() => { setMessages(conversation); setHistoryOpen(false); }}>{conversation[0]?.text.slice(0, 60)}</button>)}{!history.length && <p>新建对话后，上一段对话会显示在这里。刷新重置。</p>}</div>}
  </section>;
}
