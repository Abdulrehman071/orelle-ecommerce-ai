// Renders STRUCTURED figures returned by the assistant's database tools (not text written by the AI).
const money = (n, cur = 'PKR') => (n == null ? '—' : `${cur} ${Number(n).toLocaleString()}`);

function Stat({ label, value, sub }) {
  return (
    <div className="border border-line p-3 bg-white/40">
      <p className="font-mono text-[11px] uppercase text-ink-soft">{label}</p>
      <p className="font-mono text-lg">{value}</p>
      {sub && <p className="font-mono text-[11px] text-ink-soft">{sub}</p>}
    </div>
  );
}

const pct = (v) => (v == null ? 'no earlier data' : `${v > 0 ? '+' : ''}${v}% vs previous period`);

function SummaryCards({ s, change, title }) {
  return (
    <div>
      {title && <p className="font-mono text-xs mb-2">{title}</p>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Stat label="Revenue" value={money(s.revenue, s.currency)} sub={change ? pct(change.revenue_percent) : null} />
        <Stat label="Orders" value={Number(s.orders).toLocaleString()} sub={change ? pct(change.orders_percent) : `${s.cancelled_orders} cancelled (excluded)`} />
        <Stat label="Units sold" value={Number(s.units_sold).toLocaleString()} />
        <Stat label="Avg order" value={money(s.average_order_value == null ? null : Math.round(s.average_order_value), s.currency)} />
      </div>
    </div>
  );
}

export function BarChart({ points, field = 'revenue', label = 'Revenue' }) {
  const max = Math.max(1, ...points.map((p) => p[field] || 0));
  return (
    <div>
      <p className="font-mono text-xs mb-2">{label} by period</p>
      <div className="overflow-x-auto">
        <div role="img" aria-label={`${label} bar chart`} className="flex items-end gap-px h-40 border-b border-ink" style={{ minWidth: `${points.length * 10}px` }}>
          {points.map((p) => (
            <div key={p.period} title={`${p.period}: ${money(p[field])} (${p.orders} orders)`} className="flex-1 min-w-[6px] bg-ink hover:bg-signal"
                 style={{ height: `${Math.max(1, ((p[field] || 0) / max) * 100)}%`, opacity: p[field] ? 1 : 0.15 }} />
          ))}
        </div>
      </div>
      <div className="flex justify-between font-mono text-[11px] text-ink-soft mt-1">
        <span>{points[0]?.period}</span><span>{points[points.length - 1]?.period}</span>
      </div>
    </div>
  );
}

function Table({ cols, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="text-left font-mono text-[11px] uppercase text-ink-soft border-b border-line">
          {cols.map((c) => <th key={c.k} className="py-1 pr-4 font-normal">{c.h}</th>)}
        </tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-line/60">{cols.map((c) => <td key={c.k} className="py-1 pr-4 font-mono text-xs">{c.f ? c.f(r[c.k], r) : r[c.k]}</td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

export default function Results({ structured }) {
  const a = structured?.tools?.analytics;
  if (!a) return null;
  const blocks = [];
  (a.period_report || []).forEach((r, i) => {
    blocks.push(<SummaryCards key={`pr${i}`} s={r.summary} change={r.change_vs_previous} title={`${r.period} report · ${r.start_date} to ${r.end_date}`} />);
    if (r.top_products?.length) blocks.push(<Table key={`pt${i}`} cols={[{ k: 'rank', h: '#' }, { k: 'sku', h: 'SKU' }, { k: 'name', h: 'Product' }, { k: 'units', h: 'Units' }, { k: 'revenue', h: 'Revenue', f: (v) => money(v) }]} rows={r.top_products} />);
  });
  (a.sales_summary || []).forEach((s, i) => blocks.push(<SummaryCards key={`ss${i}`} s={s} title={`${s.start_date} to ${s.end_date}`} />));
  (a.sales_trend || []).forEach((t, i) => blocks.push(<BarChart key={`tr${i}`} points={t.points} />));
  (a.best_selling_products || []).forEach((b, i) => blocks.push(
    <Table key={`bs${i}`} cols={[{ k: 'rank', h: '#' }, { k: 'sku', h: 'SKU' }, { k: 'name', h: 'Product' }, { k: 'units', h: 'Units' }, { k: 'revenue', h: 'Revenue', f: (v) => money(v) }]} rows={b.products} />));
  (a.low_stock_report || []).forEach((l, i) => blocks.push(
    <div key={`ls${i}`}>
      <p className="font-mono text-xs mb-2">{l.variants_flagged} variants at or below {l.threshold} units ({l.out_of_stock_variants} out of stock) · showing {l.shown}</p>
      <Table cols={[{ k: 'sku', h: 'SKU' }, { k: 'name', h: 'Product' }, { k: 'color', h: 'Color' }, { k: 'size', h: 'Size' }, { k: 'stock', h: 'Stock' }]} rows={l.items} />
    </div>));
  if (!blocks.length) return null;
  return (
    <div className="mt-3 border border-ink p-3 space-y-4 bg-white/40">
      <p className="font-mono text-[11px] uppercase tracking-wide">Actual figures · calculated from the store database</p>
      {blocks}
    </div>
  );
}
