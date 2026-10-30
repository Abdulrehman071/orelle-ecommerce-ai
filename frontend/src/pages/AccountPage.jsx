import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { orderApi, addressApi } from '../api/endpoints';

const TABS = ['Orders', 'Profile', 'Addresses'];

export default function AccountPage() {
  const { user, ready, logout } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState('Orders');
  const [orders, setOrders] = useState([]);
  const [addresses, setAddresses] = useState([]);

  useEffect(() => {
    if (ready && !user) navigate('/login?next=/account');
  }, [ready, user]);

  useEffect(() => {
    if (!user) return;
    orderApi.myOrders().then((res) => setOrders(res.data.results || res.data));
    addressApi.list().then((res) => setAddresses(res.data.results || res.data));
  }, [user]);

  if (!user) return null;

  return (
    <div className="max-w-[1200px] mx-auto px-4 md:px-8 py-10">
      <h1 className="font-display text-3xl md:text-4xl uppercase mb-8">My Account</h1>
      <div className="grid md:grid-cols-4 gap-10">
        <nav className="space-y-1">
          {TABS.map((t) => (
            <button
              key={t} onClick={() => setTab(t)}
              className={`block w-full text-left px-3 py-2 font-display uppercase tracking-widest2 text-sm ${tab === t ? 'bg-ink text-paper' : 'hover:bg-paper-dim'}`}
            >
              {t}
            </button>
          ))}
          <button onClick={() => { logout(); navigate('/'); }} className="block w-full text-left px-3 py-2 font-display uppercase tracking-widest2 text-sm text-signal">
            Logout
          </button>
        </nav>

        <div className="md:col-span-3">
          {tab === 'Orders' && (
            <div className="space-y-4">
              {orders.length === 0 ? (
                <p className="text-sm text-ink-soft">No orders yet.</p>
              ) : orders.map((o) => (
                <Link key={o.id} to={`/order-confirmation/${o.order_number}`} className="block border border-line p-4 hover:border-ink">
                  <div className="flex justify-between">
                    <span className="font-mono text-sm">{o.order_number}</span>
                    <span className="font-mono text-xs uppercase text-ink-soft">{o.status}</span>
                  </div>
                  <div className="flex justify-between mt-2 text-sm text-ink-soft">
                    <span>{new Date(o.created_at).toLocaleDateString()}</span>
                    <span className="font-mono">PKR {Number(o.total).toLocaleString()}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {tab === 'Profile' && (
            <div className="space-y-3 text-sm">
              <p><span className="text-ink-soft">Name:</span> {user.first_name} {user.last_name}</p>
              <p><span className="text-ink-soft">Email:</span> {user.email}</p>
              <p><span className="text-ink-soft">Phone:</span> {user.phone || '—'}</p>
            </div>
          )}

          {tab === 'Addresses' && (
            <div className="space-y-4">
              {addresses.length === 0 ? (
                <p className="text-sm text-ink-soft">No saved addresses yet.</p>
              ) : addresses.map((a) => (
                <div key={a.id} className="border border-line p-4 text-sm">
                  <p className="font-medium">{a.full_name}</p>
                  <p className="text-ink-soft">{a.address_line}, {a.city}, {a.province}</p>
                  <p className="text-ink-soft font-mono text-xs mt-1">{a.phone}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
