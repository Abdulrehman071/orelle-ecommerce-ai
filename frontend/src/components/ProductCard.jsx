import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { wishlistApi } from '../api/endpoints';

export default function ProductCard({ product }) {
  const { user } = useAuth();
  const [wished, setWished] = useState(false);

  const toggleWishlist = async (e) => {
    e.preventDefault();
    if (!user) return;
    try {
      if (wished) {
        await wishlistApi.remove(product.id);
      } else {
        await wishlistApi.add(product.id);
      }
      setWished(!wished);
    } catch (err) { /* ignore */ }
  };

  return (
    <Link to={`/product/${product.slug}`} className="group block">
      <div className="relative overflow-hidden bg-paper-dim aspect-[4/5]">
        {product.main_image ? (
          <img
            src={product.main_image}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-ink-soft font-mono text-xs">NO IMAGE</div>
        )}

        {product.discount_percent > 0 && (
          <div className="absolute top-3 left-0 bg-signal text-paper font-mono text-xs px-2 py-1 tag-notch">
            -{product.discount_percent}%
          </div>
        )}
        {product.is_new_arrival && !product.discount_percent && (
          <div className="absolute top-3 left-0 bg-ink text-paper font-mono text-xs px-2 py-1 tag-notch">
            NEW
          </div>
        )}
        {!product.in_stock && (
          <div className="absolute inset-0 bg-paper/70 flex items-center justify-center">
            <span className="font-display uppercase tracking-widest2 text-sm">Sold Out</span>
          </div>
        )}

        <button
          onClick={toggleWishlist}
          aria-label="Toggle wishlist"
          className="absolute top-3 right-3 bg-paper/90 rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <Heart size={16} fill={wished ? '#FF3B24' : 'none'} color={wished ? '#FF3B24' : '#121212'} />
        </button>

        {product.colors?.length > 1 && (
          <div className="absolute bottom-3 left-3 flex gap-1">
            {product.colors.slice(0, 4).map((c) => (
              <span key={c.id} className="w-3.5 h-3.5 rounded-full border border-paper" style={{ backgroundColor: c.hex_code }} />
            ))}
          </div>
        )}
      </div>

      <div className="mt-3">
        <p className="text-xs text-ink-soft font-mono uppercase tracking-wide">{product.category_name}</p>
        <h3 className="font-body text-sm mt-0.5 leading-snug">{product.name}</h3>
        <div className="flex items-center gap-2 mt-1 font-mono text-sm">
          <span className={product.discount_percent > 0 ? 'text-signal' : ''}>
            PKR {Number(product.current_price).toLocaleString()}
          </span>
          {product.discount_percent > 0 && (
            <span className="text-ink-soft line-through text-xs">PKR {Number(product.price).toLocaleString()}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
