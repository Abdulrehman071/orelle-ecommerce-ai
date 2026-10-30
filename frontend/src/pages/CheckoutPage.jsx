import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { orderApi, promoApi } from '../api/endpoints';

const PROVINCES = ['Punjab', 'Sindh', 'Khyber Pakhtunkhwa', 'Balochistan', 'Gilgit-Baltistan', 'Islamabad Capital Territory'];

export default function CheckoutPage() {
  const { cart, refreshCart } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: user?.email || '',
    phone: user?.phone || '',
    shipping_full_name: '',
    shipping_address: '',
    shipping_city: '',
    shipping_province: 'Punjab',
    shipping_postal_code: '',
    delivery_method: 'standard',
    payment_method: 'cod',
  });
  const [couponCode, setCouponCode] = useState('');
  const [couponResult, setCouponResult] = useState(null);
  const [couponError, setCouponError] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const subtotal = Number(cart?.subtotal || 0);
  const shippingFee = subtotal >= 5000 ? 0 : (form.delivery_method === 'express' ? 600 : 250);
  const discount = couponResult?.valid ? Number(couponResult.discount_amount) : 0;
  const total = subtotal + shippingFee - discount;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const applyCoupon = async () => {
    setCouponError('');
    setCouponResult(null);
    try {
      const res = await promoApi.validateCoupon(couponCode, subtotal);
      setCouponResult(res.data);
    } catch (err) {
      setCouponError(err.response?.data?.detail || 'Invalid coupon.');
    }
  };

  const placeOrder = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const res = await orderApi.checkout({ ...form, coupon_code: couponResult?.valid ? couponCode : '' });
      await refreshCart();
      navigate(`/order-confirmation/${res.data.order_number}`, { state: { order: res.data } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong placing your order.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!cart || cart.items?.length === 0) {
    return <div className="text-center py-32 font-mono text-sm text-ink-soft">Your bag is empty.</div>;
  }

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-10">
      <h1 className="font-display text-3xl md:text-4xl uppercase mb-8">Checkout</h1>
      <div className="grid md:grid-cols-3 gap-12">
        <form onSubmit={placeOrder} className="md:col-span-2 space-y-10">
          <FormSection step="1" title="Contact">
            <div className="grid md:grid-cols-2 gap-4">
              <Field label="Email" type="email" value={form.email} onChange={set('email')} />
              <Field label="Phone" value={form.phone} onChange={set('phone')} />
            </div>
          </FormSection>

          <FormSection step="2" title="Shipping">
            <div className="space-y-4">
              <Field label="Full Name" value={form.shipping_full_name} onChange={set('shipping_full_name')} />
              <Field label="Address" value={form.shipping_address} onChange={set('shipping_address')} />
              <div className="grid md:grid-cols-3 gap-4">
                <Field label="City" value={form.shipping_city} onChange={set('shipping_city')} />
                <label className="block">
                  <span className="text-xs font-mono uppercase tracking-widest2 text-ink-soft">Province</span>
                  <select value={form.shipping_province} onChange={set('shipping_province')} className="w-full border-b border-line py-2 mt-1 bg-transparent outline-none">
                    {PROVINCES.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </label>
                <Field label="Postal Code" value={form.shipping_postal_code} onChange={set('shipping_postal_code')} required={false} />
              </div>
            </div>
          </FormSection>

          <FormSection step="3" title="Delivery">
            <div className="space-y-2">
              {[
                { value: 'standard', label: 'Standard Delivery', sub: '5-7 working days' },
                { value: 'express', label: 'Express Delivery', sub: '2-4 working days' },
              ].map((opt) => (
                <label key={opt.value} className={`flex justify-between items-center border p-4 cursor-pointer ${form.delivery_method === opt.value ? 'border-ink' : 'border-line'}`}>
                  <div className="flex items-center gap-3">
                    <input type="radio" checked={form.delivery_method === opt.value} onChange={() => setForm({ ...form, delivery_method: opt.value })} />
                    <div><p className="text-sm">{opt.label}</p><p className="text-xs text-ink-soft font-mono">{opt.sub}</p></div>
                  </div>
                  <span className="font-mono text-sm">{subtotal >= 5000 ? 'Free' : (opt.value === 'express' ? 'PKR 600' : 'PKR 250')}</span>
                </label>
              ))}
            </div>
          </FormSection>

          <FormSection step="4" title="Payment">
            <div className="space-y-2">
              {[
                { value: 'cod', label: 'Cash on Delivery' },
                { value: 'bank_transfer', label: 'Bank Transfer' },
                { value: 'card', label: 'Card' },
              ].map((opt) => (
                <label key={opt.value} className={`flex items-center gap-3 border p-4 cursor-pointer ${form.payment_method === opt.value ? 'border-ink' : 'border-line'}`}>
                  <input type="radio" checked={form.payment_method === opt.value} onChange={() => setForm({ ...form, payment_method: opt.value })} />
                  <span className="text-sm">{opt.label}</span>
                </label>
              ))}
            </div>
          </FormSection>

          {error && <p className="text-signal text-sm font-mono">{error}</p>}
          <button disabled={submitting} className="w-full bg-ink text-paper py-4 font-display uppercase tracking-widest2 hover:bg-signal transition-colors disabled:opacity-50">
            {submitting ? 'Placing Order...' : 'Place Order'}
          </button>
        </form>

        {/* Order summary */}
        <div className="bg-paper-dim p-6 h-fit sticky top-24">
          <h2 className="font-display uppercase text-lg mb-4">Order Summary</h2>
          <div className="divide-y divide-line max-h-64 overflow-y-auto mb-4">
            {cart.items.map((item) => (
              <div key={item.id} className="flex justify-between py-2 text-sm">
                <span>{item.quantity} × {item.product_name} ({item.variant.size.label})</span>
                <span className="font-mono">PKR {Number(item.line_total).toLocaleString()}</span>
              </div>
            ))}
          </div>

          <div className="flex gap-2 mb-4">
            <input
              value={couponCode} onChange={(e) => setCouponCode(e.target.value)}
              placeholder="Promo code" className="flex-1 border border-line px-3 py-2 text-sm outline-none"
            />
            <button type="button" onClick={applyCoupon} className="bg-ink text-paper px-4 font-mono text-xs uppercase">Apply</button>
          </div>
          {couponError && <p className="text-signal text-xs font-mono mb-2">{couponError}</p>}
          {couponResult?.valid && <p className="text-xs font-mono mb-2">Coupon "{couponResult.code}" applied.</p>}

          <div className="space-y-2 text-sm font-mono">
            <div className="flex justify-between"><span>Subtotal</span><span>PKR {subtotal.toLocaleString()}</span></div>
            <div className="flex justify-between"><span>Shipping</span><span>{shippingFee === 0 ? 'Free' : `PKR ${shippingFee}`}</span></div>
            {discount > 0 && <div className="flex justify-between text-signal"><span>Discount</span><span>-PKR {discount.toLocaleString()}</span></div>}
          </div>
          <div className="flex justify-between font-mono text-base border-t border-line mt-4 pt-4">
            <span>Total</span><span>PKR {total.toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function FormSection({ step, title, children }) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="font-mono text-xs border border-ink rounded-full w-6 h-6 flex items-center justify-center">{step}</span>
        <h2 className="font-display uppercase tracking-widest2 text-sm">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Field({ label, type = 'text', value, onChange, required = true }) {
  return (
    <label className="block">
      <span className="text-xs font-mono uppercase tracking-widest2 text-ink-soft">{label}</span>
      <input
        type={type} required={required} value={value} onChange={onChange}
        className="w-full border-b border-line focus:border-ink outline-none py-2 mt-1 bg-transparent"
      />
    </label>
  );
}
