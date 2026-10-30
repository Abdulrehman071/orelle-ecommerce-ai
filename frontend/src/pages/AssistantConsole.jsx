import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Send } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { assistantApi, assistantError } from '../api/assistant';
import { useAssistantChat } from '../hooks/useAssistantChat';
import Results from '../components/assistant/Results';
import DraftCard from '../components/assistant/DraftCard';

const PROMPTS = [
  "Give me this month's sales report",
  'Which products are low on stock?',
  "Analyze this month's sales, find the best-selling product and write an Instagram caption for it",
  'Write a product description for OF-1001 in a friendly tone',
];
const STATUS_STYLE = { completed: 'bg-ink text-paper', partial: 'bg-paper-dim', failed: 'bg-signal text-paper', refused: 'border border-line' };

export default function AssistantConsole() {
  const { user, ready } = useAuth();
  const [role, setRole] = useState(null);
  const [tab, setTab] = useState('chat');
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!ready || !user) return;
    assistantApi.me().then((r) => setRole(r.data.role)).catch((e) => setLoadError(assistantError(e)));
  }, [ready, user]);

  if (!ready) return <Wrap><p className="font-mono text-sm">Loading…</p></Wrap>;
  if (!user) return <Wrap><p className="mb-4">Please log in with a staff or admin account to use the business assistant.</p><Link to="/login" className="inline-block bg-ink text-paper px-8 py-3 font-display uppercase tracking-widest2">Log in</Link></Wrap>;
  if (loadError) return <Wrap><p role="alert" className="text-signal">{loadError}</p></Wrap>;
  if (!role) return <Wrap><p className="font-mono text-sm">Checking access…</p></Wrap>;
  if (!['staff', 'admin'].includes(role)) return <Wrap><p>Your account does not have access to the business assistant. Ask the store owner to give you the staff role.</p></Wrap>;

  return (
    <Wrap>
      <div className="flex items-end justify-between flex-wrap gap-2 mb-6">
        <h1 className="font-display uppercase tracking-widest2 text-3xl">Business Assistant</h1>
        <span className="font-mono text-xs text-ink-soft">Signed in as {user.email} · role: {role}</span>
      </div>
      <div className="flex border-b border-line mb-6" role="tablist">
        {[['chat', 'Chat'], ['drafts', 'Drafts & review'], ['activity', 'Activity']].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                  className={`px-4 py-2 font-display uppercase tracking-widest2 text-sm border-b-2 -mb-px ${tab === k ? 'border-ink' : 'border-transparent text-ink-soft'}`}>{l}</button>
        ))}
      </div>
      {tab === 'chat' && <ChatTab role={role} />}
      {tab === 'drafts' && <DraftsTab />}
      {tab === 'activity' && <ActivityTab />}
    </Wrap>
  );
}

const Wrap = ({ children }) => <div className="max-w-5xl mx-auto px-4 py-10">{children}</div>;

function ChatTab({ role }) {
  const { messages, loading, send, reset } = useAssistantChat();
  const [input, setInput] = useState('');
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);
  const submit = (e) => { e.preventDefault(); if (input.trim()) { send(input); setInput(''); } };

  return (
    <div>
      {role !== 'admin' && <p className="font-mono text-xs text-ink-soft mb-3">Staff accounts can draft marketing and view stock. Revenue and sales reports need the admin role.</p>}
      <div className="space-y-4 min-h-[16rem]" aria-live="polite">
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {PROMPTS.map((p) => <button key={p} onClick={() => send(p)} className="border border-line px-3 py-2 text-sm text-left hover:border-ink">{p}</button>)}
          </div>
        )}
        {messages.map((m) => <Message key={m.id} m={m} />)}
        {loading && <p className="font-mono text-sm animate-pulse">Working on it — the agents may call several tools…</p>}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="flex border border-ink mt-6">
        <input value={input} onChange={(e) => setInput(e.target.value)} disabled={loading} maxLength={2000} aria-label="Your request"
               placeholder="e.g. Analyze this month's sales and write a promo post for the best seller"
               className="flex-1 px-4 py-3 bg-transparent outline-none disabled:opacity-50" />
        <button disabled={loading || !input.trim()} className="px-5 bg-ink text-paper hover:bg-signal disabled:opacity-40 flex items-center gap-2 font-display uppercase tracking-widest2 text-sm">
          <Send size={16} /> Send
        </button>
        {messages.length > 0 && <button type="button" onClick={reset} className="px-4 font-mono text-xs uppercase text-ink-soft hover:text-signal">Clear</button>}
      </form>
    </div>
  );
}

function Message({ m }) {
  const [drafts, setDrafts] = useState(m.data?.structured?.drafts || []);
  if (m.role === 'user') return <div className="flex justify-end"><p className="bg-ink text-paper px-4 py-2 max-w-[85%] whitespace-pre-wrap">{m.text}</p></div>;
  if (m.role === 'error') return <p role="alert" className="border border-signal text-signal px-4 py-2">{m.text}</p>;
  const d = m.data;
  return (
    <div className="max-w-full">
      <div className="bg-paper-dim px-4 py-3">
        <p className="font-mono text-[11px] uppercase text-ink-soft mb-1">AI summary — wording only; figures below come from the database</p>
        <p className="whitespace-pre-wrap">{m.text}</p>
      </div>
      <Results structured={d?.structured} />
      {drafts.length > 0 && (
        <div className="mt-3 space-y-3">
          <p className="font-mono text-[11px] uppercase">AI-generated drafts · edit, then approve or reject</p>
          {drafts.map((dr) => <DraftCard key={dr.id} draft={dr} onChange={(u) => setDrafts((p) => p.map((x) => (x.id === u.id ? u : x)))} />)}
        </div>
      )}
      {d?.steps?.length > 0 && (
        <details className="mt-2 font-mono text-[11px] text-ink-soft">
          <summary className="cursor-pointer">How this was answered ({d.status}, {d.duration_ms} ms)</summary>
          <ul className="mt-1 space-y-1">
            {d.steps.map((s, i) => (
              <li key={i}>{i + 1}. <b>{s.agent}</b> → {s.status}{s.error ? ` (${s.error})` : ''} · tools: {s.tools.length ? s.tools.map((t) => `${t.tool}[${t.status}]`).join(', ') : 'none'}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function DraftsTab() {
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState('open');
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    assistantApi.drafts({ limit: 100 }).then((r) => setItems(r.data.items)).catch((e) => setError(assistantError(e)));
  }, []);
  useEffect(load, [load]);
  if (error) return <p role="alert" className="text-signal">{error}</p>;
  if (!items) return <p className="font-mono text-sm">Loading…</p>;
  const shown = items.filter((d) => (filter === 'open' ? ['draft', 'pending_review'].includes(d.status) : true));
  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-center">
        {[['open', 'Needs review'], ['all', 'All']].map(([k, l]) => (
          <button key={k} onClick={() => setFilter(k)} className={`px-3 py-1 font-mono text-xs uppercase border ${filter === k ? 'border-ink bg-ink text-paper' : 'border-line'}`}>{l}</button>
        ))}
        <button onClick={load} className="ml-auto font-mono text-xs uppercase underline">Refresh</button>
      </div>
      {shown.length === 0 && <p className="text-ink-soft">Nothing here. Ask the assistant to draft marketing content, or customer questions it escalates will appear for review.</p>}
      {shown.map((d) => <DraftCard key={d.id} draft={d} onChange={(u) => setItems((p) => p.map((x) => (x.id === u.id ? u : x)))} />)}
    </div>
  );
}

function ActivityTab() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    assistantApi.history(50).then((r) => setItems(r.data.items)).catch((e) => setError(assistantError(e)));
  }, []);
  useEffect(load, [load]);
  if (error) return <p role="alert" className="text-signal">{error}</p>;
  if (!items) return <p className="font-mono text-sm">Loading…</p>;
  return (
    <div>
      <div className="flex justify-end mb-2"><button onClick={load} className="font-mono text-xs uppercase underline">Refresh</button></div>
      {items.length === 0 && <p className="text-ink-soft">No activity yet.</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left font-mono text-[11px] uppercase text-ink-soft border-b border-line">
            {['When', 'Who', 'Request', 'Agents', 'Status', 'Time'].map((h) => <th key={h} className="py-1 pr-4 font-normal">{h}</th>)}
          </tr></thead>
          <tbody>{items.map((t) => (
            <tr key={t.task_id} className="border-b border-line/60 align-top">
              <td className="py-2 pr-4 font-mono text-xs whitespace-nowrap">{new Date(t.created_at).toLocaleString()}</td>
              <td className="py-2 pr-4 font-mono text-xs">{t.role}</td>
              <td className="py-2 pr-4 max-w-xs"><p className="truncate" title={t.request}>{t.request}</p>
                {t.error && <p className="font-mono text-[11px] text-signal">{t.error}</p>}
                {t.tools.length > 0 && <p className="font-mono text-[11px] text-ink-soft">{t.tools.map((x) => `${x.tool}${x.status !== 'ok' ? `(${x.status})` : ''}`).join(', ')}</p>}</td>
              <td className="py-2 pr-4 font-mono text-xs">{t.agents.join(' → ') || '—'}</td>
              <td className="py-2 pr-4"><span className={`font-mono text-[11px] uppercase px-2 py-0.5 ${STATUS_STYLE[t.status] || ''}`}>{t.status}</span></td>
              <td className="py-2 font-mono text-xs whitespace-nowrap">{t.duration_ms} ms</td>
            </tr>))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
