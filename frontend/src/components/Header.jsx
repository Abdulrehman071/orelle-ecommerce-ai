import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Heart, User, ShoppingBag, Menu, X } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { promoApi, catalogApi } from '../api/endpoints';

const NAV_LINKS = [
  { label: 'Men', to: '/category/men' },
  { label: 'Women', to: '/category/women' },
  { label: 'Juniors', to: '/category/juniors' },
  { label: 'New In', to: '/new-in' },
  { label: 'Sale', to: '/sale', signal: true },
];

export default function Header() {
  const { cart } = useCart();
  const { user } = useAuth();
  const [announcement, setAnnouncement] = useState('FREE DELIVERY ON ORDERS ABOVE PKR 5,000');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    promoApi.banners('announcement').then((res) => {
      if (res.data.results?.[0]) setAnnouncement(res.data.results[0].message);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); return; }
    const t = setTimeout(() => {
      catalogApi.searchSuggestions(query).then((res) => setSuggestions(res.data)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  const submitSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    navigate(`/search?q=${encodeURIComponent(query)}`);
    setSearchOpen(false);
    setQuery('');
  };

  return (
    <header className="sticky top-0 z-40 bg-paper">
      {/* Announcement marquee - signature runway-ticker element */}
      <div className="bg-ink text-paper overflow-hidden whitespace-nowrap py-2">
        <div className="animate-marquee inline-block font-mono text-[11px] tracking-widest2 uppercase">
          {Array(6).fill(announcement).map((t, i) => (
            <span key={i} className="mx-8">{t}</span>
          ))}
        </div>
      </div>

      {/* Main nav */}
      <div className="border-b border-line">
        <div className="max-w-[1400px] mx-auto px-4 md:px-8 flex items-center justify-between h-16">
          <button className="md:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu size={22} />
          </button>

          <Link to="/" className="font-display text-2xl md:text-3xl tracking-widest2 uppercase font-semibold">
            Orelle
          </Link>

          <nav className="hidden md:flex items-center gap-8 font-display uppercase text-sm tracking-widest2">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={link.signal ? 'text-signal hover:text-signal-dim' : 'hover:text-ink-soft transition-colors'}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-4 md:gap-5">
            <button onClick={() => setSearchOpen(true)} aria-label="Search"><Search size={20} /></button>
            <Link to="/wishlist" aria-label="Wishlist" className="hidden sm:block"><Heart size={20} /></Link>
            <Link to={user ? '/account' : '/login'} aria-label="Account" className="hidden sm:block"><User size={20} /></Link>
            <Link to="/cart" aria-label="Cart" className="relative">
              <ShoppingBag size={20} />
              {cart?.total_items > 0 && (
                <span className="absolute -top-2 -right-2 bg-signal text-paper text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-mono">
                  {cart.total_items}
                </span>
              )}
            </Link>
          </div>
        </div>
      </div>

      {/* Search overlay */}
      {searchOpen && (
        <div className="absolute inset-x-0 top-0 bg-paper border-b border-line shadow-lg z-50">
          <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-4">
            <form onSubmit={submitSearch} className="flex items-center gap-3 border-b border-ink pb-2">
              <Search size={18} />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search for products, e.g. black shirt"
                className="flex-1 bg-transparent outline-none font-body text-lg"
              />
              <button type="button" onClick={() => setSearchOpen(false)} aria-label="Close search"><X size={20} /></button>
            </form>
            {suggestions.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mt-4">
                {suggestions.map((p) => (
                  <Link
                    key={p.id}
                    to={`/product/${p.slug}`}
                    onClick={() => setSearchOpen(false)}
                    className="text-sm hover:underline"
                  >
                    {p.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 bg-paper flex flex-col">
          <div className="flex justify-between items-center px-4 h-16 border-b border-line">
            <span className="font-display text-xl tracking-widest2 uppercase">Orelle</span>
            <button onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={24} /></button>
          </div>
          <nav className="flex flex-col gap-1 p-4 font-display uppercase text-2xl">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileOpen(false)}
                className={`py-3 border-b border-line ${link.signal ? 'text-signal' : ''}`}
              >
                {link.label}
              </Link>
            ))}
            <Link to="/wishlist" onClick={() => setMobileOpen(false)} className="py-3 border-b border-line">Wishlist</Link>
            <Link to={user ? '/account' : '/login'} onClick={() => setMobileOpen(false)} className="py-3 border-b border-line">
              {user ? 'My Account' : 'Login / Register'}
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
