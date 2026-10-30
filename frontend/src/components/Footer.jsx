import { useState } from 'react';
import { Link } from 'react-router-dom';
import { storefrontApi } from '../api/endpoints';

const COLUMNS = [
  {
    title: 'Shop',
    links: [
      { label: 'Men', to: '/category/men' },
      { label: 'Women', to: '/category/women' },
      { label: 'Juniors', to: '/category/juniors' },
      { label: 'New In', to: '/new-in' },
      { label: 'Sale', to: '/sale' },
    ],
  },
  {
    title: 'Customer Care',
    links: [
      { label: 'Contact Us', to: '/info/contact' },
      { label: 'FAQ', to: '/info/faq' },
      { label: 'Shipping', to: '/info/shipping' },
      { label: 'Returns', to: '/info/returns' },
      { label: 'Size Guide', to: '/info/size-guide' },
    ],
  },
  {
    title: 'About',
    links: [
      { label: 'About Us', to: '/info/about' },
      { label: 'Store Locator', to: '/stores' },
      { label: 'Privacy Policy', to: '/info/privacy' },
    ],
  },
];

export default function Footer() {
  const [email, setEmail] = useState('');
  const [done, setDone] = useState(false);

  const subscribe = async (e) => {
    e.preventDefault();
    if (!email) return;
    try {
      await storefrontApi.subscribeNewsletter(email);
      setDone(true);
      setEmail('');
    } catch (err) { /* ignore duplicate */ setDone(true); }
  };

  return (
    <footer className="bg-ink text-paper mt-24">
      <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-16 grid md:grid-cols-4 gap-12">
        <div>
          <p className="font-display uppercase tracking-widest2 text-xs text-paper/60 mb-3">Be the first to know</p>
          <h3 className="font-display text-2xl uppercase mb-4">Join the list</h3>
          {done ? (
            <p className="text-sm text-paper/70">You're on the list. Watch your inbox.</p>
          ) : (
            <form onSubmit={subscribe} className="flex border-b border-paper/40 pb-2">
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                required
                placeholder="Enter your email"
                className="bg-transparent flex-1 outline-none placeholder:text-paper/40 text-sm"
              />
              <button type="submit" className="font-mono text-xs uppercase tracking-widest2">Sign up</button>
            </form>
          )}
          <div className="flex gap-4 mt-6 text-xs uppercase tracking-widest2 text-paper/60">
            <a href="#" className="hover:text-paper">Instagram</a>
            <a href="#" className="hover:text-paper">TikTok</a>
            <a href="#" className="hover:text-paper">Facebook</a>
          </div>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.title}>
            <p className="font-display uppercase tracking-widest2 text-xs text-paper/60 mb-4">{col.title}</p>
            <ul className="space-y-2">
              {col.links.map((l) => (
                <li key={l.label}>
                  <Link to={l.to} className="text-sm text-paper/85 hover:text-paper">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-paper/15 py-5 text-center text-xs text-paper/50 font-mono">
        © 2026 ORELLE. ALL RIGHTS RESERVED.
      </div>
    </footer>
  );
}
