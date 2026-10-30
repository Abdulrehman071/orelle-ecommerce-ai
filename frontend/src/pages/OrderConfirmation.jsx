import { useLocation, useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { orderApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';

export default function OrderConfirmation() {
  const { orderNumber } = useParams();
  const location = useLocation();
  const { user } = useAuth();
  const [order, setOrder] = useState(location.state?.order || null);

  useEffect(() => {
    if (!order && user) {
      orderApi.detail(orderNumber).then((res) => setOrder(res.data)).catch(() => {});
    }
  }, [order, user, orderNumber]);

  return (
    <div className="max-w-xl mx-auto px-4 py-24 text-center">
      <div className="w-16 h-16 rounded-full bg-ink text-paper flex items-center justify-center mx-auto mb-6">
        <Check size={28} />
      </div>
      <h1 className="font-display text-3xl uppercase mb-2">Order Placed</h1>
      <p className="text-ink-soft mb-6">Thank you for your order!</p>
      <p className="font-mono text-lg mb-1">Order #: {orderNumber}</p>
      <p className="text-sm text-ink-soft font-mono mb-10">
        Estimated Delivery: {order?.shipment?.estimated_delivery_days || '5-7'} working days
      </p>

      {order && (
        <div className="text-left border border-line p-6 mb-10">
          <div className="divide-y divide-line">
            {order.items?.map((item) => (
              <div key={item.id} className="flex justify-between py-2 text-sm">
                <span>{item.quantity} × {item.product_name} ({item.size_label})</span>
                <span className="font-mono">PKR {Number(item.line_total).toLocaleString()}</span>
              </div>
            ))}
          </div>
          <div className="flex justify-between font-mono text-base border-t border-line mt-4 pt-4">
            <span>Total</span><span>PKR {Number(order.total).toLocaleString()}</span>
          </div>
        </div>
      )}

      <div className="flex gap-4 justify-center">
        <Link to={`/track-order?order=${orderNumber}`} className="border border-ink px-6 py-3 font-display uppercase tracking-widest2 text-sm">
          Track Order
        </Link>
        <Link to="/" className="bg-ink text-paper px-6 py-3 font-display uppercase tracking-widest2 text-sm">
          Continue Shopping
        </Link>
      </div>
    </div>
  );
}
