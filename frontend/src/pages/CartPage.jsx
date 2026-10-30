import { Link } from 'react-router-dom';
import { Minus, Plus, X } from 'lucide-react';
import { useCart } from '../context/CartContext';

export default function CartPage() {
  const { cart, updateItem, removeItem } = useCart();
  const items = cart?.items || [];
  const shippingFee = cart?.subtotal >= 5000 ? 0 : 250;
  const total = Number(cart?.subtotal || 0) + shippingFee;

  if (items.length === 0) {
    return (
      <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-32 text-center">
        <h1 className="font-display text-3xl uppercase mb-4">Your Bag is Empty</h1>
        <Link to="/" className="inline-block bg-ink text-paper px-8 py-3 font-display uppercase tracking-widest2">
          Continue Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-10">
      <h1 className="font-display text-3xl md:text-4xl uppercase mb-8">Shopping Bag</h1>
      <div className="grid md:grid-cols-3 gap-12">
        <div className="md:col-span-2 divide-y divide-line">
          {items.map((item) => (
            <div key={item.id} className="flex gap-4 py-6">
              <Link to={`/product/${item.product_slug}`} className="w-24 h-32 bg-paper-dim shrink-0 overflow-hidden">
                {item.product_image && <img src={item.product_image} alt="" className="w-full h-full object-cover" />}
              </Link>
              <div className="flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between">
                    <Link to={`/product/${item.product_slug}`} className="font-body text-sm hover:underline">{item.product_name}</Link>
                    <button onClick={() => removeItem(item.id)} aria-label="Remove"><X size={16} className="text-ink-soft" /></button>
                  </div>
                  <p className="text-xs text-ink-soft font-mono mt-1">Size: {item.variant.size.label} / Color: {item.variant.color.name}</p>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center border border-line">
                    <button onClick={() => updateItem(item.id, item.quantity - 1)} className="p-2"><Minus size={12} /></button>
                    <span className="px-3 font-mono text-sm">{item.quantity}</span>
                    <button onClick={() => updateItem(item.id, item.quantity + 1)} className="p-2"><Plus size={12} /></button>
                  </div>
                  <span className="font-mono text-sm">PKR {Number(item.line_total).toLocaleString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-paper-dim p-6 h-fit">
          <h2 className="font-display uppercase text-lg mb-4">Order Summary</h2>
          <div className="space-y-2 text-sm font-mono">
            <div className="flex justify-between"><span>Subtotal</span><span>PKR {Number(cart.subtotal).toLocaleString()}</span></div>
            <div className="flex justify-between"><span>Shipping</span><span>{shippingFee === 0 ? 'Free' : `PKR ${shippingFee}`}</span></div>
          </div>
          <div className="flex justify-between font-mono text-base border-t border-line mt-4 pt-4">
            <span>Total</span><span>PKR {total.toLocaleString()}</span>
          </div>
          <Link to="/checkout" className="block text-center mt-6 bg-ink text-paper py-4 font-display uppercase tracking-widest2 hover:bg-signal transition-colors">
            Proceed to Checkout
          </Link>
          <Link to="/" className="block text-center mt-3 text-xs font-mono uppercase underline text-ink-soft">Continue Shopping</Link>
        </div>
      </div>
    </div>
  );
}
