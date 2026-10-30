import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import { useCart } from '../context/CartContext';

export default function MiniCart() {
  const { cart, miniCartOpen, setMiniCartOpen } = useCart();
  if (!miniCartOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/40" onClick={() => setMiniCartOpen(false)} />
      <div className="relative bg-paper w-full max-w-sm h-full flex flex-col">
        <div className="flex items-center justify-between px-5 h-16 border-b border-line">
          <span className="font-display uppercase tracking-widest2">Your Bag</span>
          <button onClick={() => setMiniCartOpen(false)} aria-label="Close"><X size={20} /></button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-line px-5">
          {cart?.items?.map((item) => (
            <div key={item.id} className="flex gap-3 py-4">
              <div className="w-16 h-20 bg-paper-dim shrink-0 overflow-hidden">
                {item.product_image && <img src={item.product_image} alt="" className="w-full h-full object-cover" />}
              </div>
              <div className="flex-1">
                <p className="text-sm">{item.product_name}</p>
                <p className="text-xs text-ink-soft font-mono">{item.variant.size.label} / {item.variant.color.name}</p>
                <p className="font-mono text-sm mt-1">PKR {Number(item.line_total).toLocaleString()}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="p-5 border-t border-line">
          <div className="flex justify-between font-mono text-sm mb-4">
            <span>Subtotal</span><span>PKR {Number(cart?.subtotal || 0).toLocaleString()}</span>
          </div>
          <Link to="/cart" onClick={() => setMiniCartOpen(false)} className="block text-center border border-ink py-3 font-display uppercase tracking-widest2 text-sm mb-2">
            View Bag
          </Link>
          <Link to="/checkout" onClick={() => setMiniCartOpen(false)} className="block text-center bg-ink text-paper py-3 font-display uppercase tracking-widest2 text-sm">
            Checkout
          </Link>
        </div>
      </div>
    </div>
  );
}
