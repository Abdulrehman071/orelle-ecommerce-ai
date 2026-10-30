import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { orderApi } from '../api/endpoints';
import { Check } from 'lucide-react';

const STEPS = ['placed', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered'];
const STEP_LABELS = { placed: 'Order Placed', confirmed: 'Confirmed', processing: 'Processing', shipped: 'Shipped', out_for_delivery: 'Out for Delivery', delivered: 'Delivered' };

export default function TrackOrderPage() {
  const [params] = useSearchParams();
  const [orderNumber, setOrderNumber] = useState(params.get('order') || '');
  const [email, setEmail] = useState('');
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');

  const lookup = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await orderApi.guestTrack(orderNumber, email);
      setOrder(res.data);
    } catch (err) {
      setError('Order not found. Check your order number and email.');
    }
  };

  const currentStepIndex = order ? STEPS.indexOf(order.status === 'cancelled' ? 'placed' : order.status) : -1;

  return (
    <div className="max-w-xl mx-auto px-4 py-16">
      <h1 className="font-display text-3xl uppercase mb-8 text-center">Track Your Order</h1>
      <form onSubmit={lookup} className="space-y-4 mb-10">
        <label className="block">
          <span className="text-xs font-mono uppercase tracking-widest2 text-ink-soft">Order Number</span>
          <input value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} required className="w-full border-b border-line py-2 mt-1 bg-transparent outline-none" placeholder="ORD-10245" />
        </label>
        <label className="block">
          <span className="text-xs font-mono uppercase tracking-widest2 text-ink-soft">Email</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full border-b border-line py-2 mt-1 bg-transparent outline-none" />
        </label>
        {error && <p className="text-signal text-xs font-mono">{error}</p>}
        <button className="w-full bg-ink text-paper py-4 font-display uppercase tracking-widest2">Track</button>
      </form>

      {order && (
        <div>
          <p className="font-mono text-sm mb-6">Order #{order.order_number}</p>
          <div className="space-y-0">
            {STEPS.map((step, i) => (
              <div key={step} className="flex items-start gap-4">
                <div className="flex flex-col items-center">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${i <= currentStepIndex ? 'bg-ink text-paper' : 'border border-line text-ink-soft'}`}>
                    {i <= currentStepIndex ? <Check size={14} /> : <span className="text-xs font-mono">{i + 1}</span>}
                  </div>
                  {i < STEPS.length - 1 && <div className={`w-px flex-1 h-8 ${i < currentStepIndex ? 'bg-ink' : 'bg-line'}`} />}
                </div>
                <p className={`text-sm pt-1 ${i <= currentStepIndex ? '' : 'text-ink-soft'}`}>{STEP_LABELS[step]}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
