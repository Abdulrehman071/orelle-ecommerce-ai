import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MessageCircle, Send, X } from 'lucide-react';
import { useAssistantChat } from '../hooks/useAssistantChat';
import { assistantApi } from '../api/assistant';

const SUGGESTIONS = ["What's your return policy?", 'Is the Leather Loafer in stock?', 'How long does delivery take?'];

// Floating customer chat. Customers only ever reach the Customer Support agent (enforced by the backend).
export default function AssistantWidget() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [isStaff, setIsStaff] = useState(false);
  const { messages, loading, send } = useAssistantChat();
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading, open]);

  useEffect(() => {
    if (!open || !localStorage.getItem('auth_token')) return;
    assistantApi.me().then((r) => setIsStaff(['staff', 'admin'].includes(r.data.role))).catch(() => {});
  }, [open]);

  if (pathname.startsWith('/assistant')) return null; // the console has its own chat

  const submit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    send(input);
    setInput('');
  };

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open shop assistant"
          className="fixed bottom-5 right-5 z-40 bg-ink text-paper w-14 h-14 flex items-center justify-center hover:bg-signal transition-colors"
        >
          <MessageCircle size={22} />
        </button>
      )}
      {open && (
        <div role="dialog" aria-label="Shop assistant"
             className="fixed z-40 bottom-0 right-0 sm:bottom-5 sm:right-5 w-full sm:w-96 h-[80vh] sm:h-[32rem] bg-paper border border-ink flex flex-col">
          <div className="flex items-center justify-between px-4 h-14 bg-ink text-paper shrink-0">
            <span className="font-display uppercase tracking-widest2 text-sm">Shop Assistant</span>
            <div className="flex items-center gap-3">
              {isStaff && <Link to="/assistant" onClick={() => setOpen(false)} className="font-mono text-xs underline">Console</Link>}
              <button onClick={() => setOpen(false)} aria-label="Close assistant"><X size={18} /></button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3" aria-live="polite">
            <Bubble role="assistant">Hi! Ask me about products, sizes, stock, delivery, returns or your order status.</Bubble>
            {messages.length === 0 && (
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="border border-line px-3 py-1.5 text-xs hover:border-ink">{s}</button>
                ))}
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id}>
                <Bubble role={m.role}>{m.text}</Bubble>
                {m.data?.escalated && <p className="font-mono text-[11px] text-ink-soft mt-1">A team member will follow up on this.</p>}
              </div>
            ))}
            {loading && <Bubble role="assistant"><span className="animate-pulse">Thinking…</span></Bubble>}
            <div ref={endRef} />
          </div>

          <form onSubmit={submit} className="flex border-t border-line shrink-0">
            <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={2000} disabled={loading}
                   placeholder="Type your question…" aria-label="Your message"
                   className="flex-1 px-4 py-3 bg-transparent outline-none text-sm disabled:opacity-50" />
            <button disabled={loading || !input.trim()} aria-label="Send" className="px-4 bg-ink text-paper hover:bg-signal transition-colors disabled:opacity-40">
              <Send size={16} />
            </button>
          </form>
        </div>
      )}
    </>
  );
}

function Bubble({ role, children }) {
  const mine = role === 'user';
  const cls = role === 'error' ? 'border border-signal text-signal' : mine ? 'bg-ink text-paper' : 'bg-paper-dim';
  return (
    <div className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] px-3 py-2 text-sm whitespace-pre-wrap break-words ${cls}`}>{children}</div>
    </div>
  );
}
