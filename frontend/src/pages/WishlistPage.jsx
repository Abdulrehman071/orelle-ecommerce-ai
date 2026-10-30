import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { wishlistApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import ProductCard from '../components/ProductCard';

export default function WishlistPage() {
  const { user, ready } = useAuth();
  const [items, setItems] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && !user) { navigate('/login?next=/wishlist'); return; }
    if (user) wishlistApi.get().then((res) => setItems(res.data.items));
  }, [user, ready]);

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-10">
      <h1 className="font-display text-3xl md:text-4xl uppercase mb-8">My Wishlist</h1>
      {items.length === 0 ? (
        <p className="text-ink-soft text-sm">Nothing here yet. <Link to="/" className="underline">Start browsing</Link>.</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-10">
          {items.map((item) => <ProductCard key={item.id} product={item.product} />)}
        </div>
      )}
    </div>
  );
}
