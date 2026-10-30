import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { assistantApi, assistantError } from '../../api/assistant';

const KIND_LABELS = {
  product_description: 'Product description', facebook_post: 'Facebook post', instagram_caption: 'Instagram caption',
  promo_message: 'Promo message', campaign_idea: 'Campaign idea', content_calendar: 'Content calendar',
  support_escalation: 'Support escalation',
};
const STATUS_STYLE = {
  draft: 'bg-paper-dim', pending_review: 'bg-signal text-paper', approved: 'bg-ink text-paper',
  resolved: 'bg-ink text-paper', rejected: 'border border-line text-ink-soft',
};

// An editable draft with human approval controls. Approving NEVER publishes or sends anything in this version.
export default function DraftCard({ draft, onChange }) {
  const [title, setTitle] = useState(draft.title);
  const [body, setBody] = useState(draft.body);
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const open = ['draft', 'pending_review'].includes(draft.status);
  const isEscalation = draft.kind === 'support_escalation';
  const dirty = title !== draft.title || body !== draft.body;

  const run = async (fn) => {
    setBusy(true); setError('');
    try { const { data } = await fn(); onChange?.(data); setTitle(data.title); setBody(data.body); setAck(false); }
    catch (e) { setError(assistantError(e)); }
    finally { setBusy(false); }
  };
  const save = () => run(() => assistantApi.editDraft(draft.id, { title, body }));
  const approve = () => run(() => assistantApi.approveDraft(draft.id, ack));
  const reject = () => run(() => assistantApi.rejectDraft(draft.id));

  return (
    <div className="border border-line bg-white/40 p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <span className="font-mono text-xs uppercase text-ink-soft">{KIND_LABELS[draft.kind] || draft.kind}</span>
        <span className={`font-mono text-[11px] uppercase px-2 py-0.5 ${STATUS_STYLE[draft.status] || ''}`}>{draft.status.replace('_', ' ')}</span>
      </div>

      {open ? (
        <>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} aria-label="Title"
                 className="w-full border-b border-line focus:border-ink outline-none py-1 bg-transparent font-display tracking-wide" />
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={Math.min(14, Math.max(5, body.split('\n').length + 1))}
                    maxLength={4000} aria-label="Draft text"
                    className="w-full border border-line focus:border-ink outline-none p-2 bg-transparent text-sm" />
        </>
      ) : (
        <>
          <p className="font-display tracking-wide">{draft.title}</p>
          <p className="text-sm whitespace-pre-wrap">{draft.body}</p>
        </>
      )}

      {draft.warnings?.length > 0 && (
        <div className="border border-signal p-3 text-xs space-y-1">
          <p className="flex items-center gap-1 font-mono uppercase text-signal"><AlertTriangle size={14} /> Fact-check warnings</p>
          {draft.warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      )}
      {draft.meta?.contact && <p className="font-mono text-xs text-ink-soft">Customer contact: {draft.meta.contact}</p>}
      {draft.review_note && <p className="font-mono text-xs text-ink-soft">Note: {draft.review_note}</p>}
      {error && <p role="alert" className="text-xs text-signal">{error}</p>}

      {open && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {dirty && <button disabled={busy} onClick={save} className="border border-ink px-3 py-1.5 font-mono text-xs uppercase hover:bg-ink hover:text-paper disabled:opacity-50">Save edits</button>}
          {draft.warnings?.length > 0 && !dirty && (
            <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> I checked these claims</label>
          )}
          <button disabled={busy || dirty || (draft.warnings?.length > 0 && !ack)} onClick={approve}
                  className="bg-ink text-paper px-3 py-1.5 font-mono text-xs uppercase hover:bg-signal disabled:opacity-40">
            {isEscalation ? 'Mark resolved' : 'Approve'}
          </button>
          <button disabled={busy} onClick={reject} className="px-3 py-1.5 font-mono text-xs uppercase text-ink-soft hover:text-signal">{isEscalation ? 'Dismiss' : 'Reject'}</button>
          {!isEscalation && <span className="font-mono text-[11px] text-ink-soft">Approving does not publish anything.</span>}
        </div>
      )}
    </div>
  );
}
