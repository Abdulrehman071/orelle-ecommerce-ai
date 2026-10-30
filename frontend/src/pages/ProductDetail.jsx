import { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Heart, Star, ChevronLeft, ChevronRight } from 'lucide-react';
import { catalogApi } from '../api/endpoints';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import ProductCard from '../components/ProductCard';

export default function ProductDetail() {
  const { slug } = useParams();
  const { addItem } = useCart();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [selectedColor, setSelectedColor] = useState(null);
  const [selectedSize, setSelectedSize] = useState(null);
  const [activeImage, setActiveImage] = useState(0);
  const [sizeGuideOpen, setSizeGuideOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [notifyEmail, setNotifyEmail] = useState('');
  const [notifySent, setNotifySent] = useState(false);

  useEffect(() => {
    setProduct(null);
    catalogApi.getProduct(slug).then((res) => {
      setProduct(res.data);
      setSelectedColor(res.data.colors?.[0]?.id ?? null);
      setActiveImage(0);
    });
    window.scrollTo(0, 0);
  }, [slug]);

  const filteredImages = useMemo(() => {
    if (!product) return [];
    const colorImages = product.images.filter((img) => img.color === selectedColor);
    return colorImages.length > 0 ? colorImages : product.images;
  }, [product, selectedColor]);

  const currentVariant = useMemo(() => {
    if (!product || !selectedColor || !selectedSize) return null;
    return product.variants.find((v) => v.color.id === selectedColor && v.size.id === selectedSize);
  }, [product, selectedColor, selectedSize]);

  const sizesForColor = useMemo(() => {
    if (!product || !selectedColor) return [];
    return product.variants.filter((v) => v.color.id === selectedColor);
  }, [product, selectedColor]);

  if (!product) {
    return <div className="text-center py-32 font-mono text-sm text-ink-soft">Loading...</div>;
  }

  const handleAddToBag = async () => {
    if (!selectedSize) { setMessage('Please select a size.'); return; }
    if (!currentVariant || currentVariant.stock === 0) { setMessage('This size is sold out.'); return; }
    const res = await addItem(currentVariant.id, 1);
    setMessage(res.ok ? 'Added to your bag.' : res.error);
  };

  const handleNotify = async () => {
    if (!currentVariant || !notifyEmail) return;
    await catalogApi.notifyBackInStock(currentVariant.id, notifyEmail);
    setNotifySent(true);
  };

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-10">
      <div className="grid md:grid-cols-2 gap-10 lg:gap-16">
        {/* Images */}
        <div>
          <div className="relative aspect-[4/5] bg-paper-dim overflow-hidden">
            {filteredImages[activeImage]?.image && (
              <img src={filteredImages[activeImage].image} alt={product.name} className="w-full h-full object-cover" />
            )}
            {filteredImages.length > 1 && (
              <>
                <button
                  onClick={() => setActiveImage((i) => (i - 1 + filteredImages.length) % filteredImages.length)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 bg-paper/80 rounded-full p-1.5"
                >
                  <ChevronLeft size={18} />
                </button>
                <button
                  onClick={() => setActiveImage((i) => (i + 1) % filteredImages.length)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 bg-paper/80 rounded-full p-1.5"
                >
                  <ChevronRight size={18} />
                </button>
              </>
            )}
          </div>
          {filteredImages.length > 1 && (
            <div className="flex gap-2 mt-3">
              {filteredImages.map((img, i) => (
                <button key={img.id} onClick={() => setActiveImage(i)} className={`w-16 h-20 shrink-0 overflow-hidden border ${activeImage === i ? 'border-ink' : 'border-transparent'}`}>
                  <img src={img.image} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Info */}
        <div>
          <p className="font-mono text-xs uppercase text-ink-soft tracking-widest2">{product.category?.name}</p>
          <h1 className="font-display text-3xl md:text-4xl uppercase mt-1">{product.name}</h1>

          {product.average_rating > 0 && (
            <div className="flex items-center gap-1 mt-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <Star key={n} size={14} fill={n <= Math.round(product.average_rating) ? '#121212' : 'none'} color="#121212" />
              ))}
              <span className="text-xs text-ink-soft ml-1 font-mono">({product.reviews.length})</span>
            </div>
          )}

          <div className="flex items-center gap-3 mt-4 font-mono text-xl">
            <span className={product.discount_percent > 0 ? 'text-signal' : ''}>
              PKR {Number(product.current_price).toLocaleString()}
            </span>
            {product.discount_percent > 0 && (
              <>
                <span className="text-ink-soft line-through text-base">PKR {Number(product.price).toLocaleString()}</span>
                <span className="bg-signal text-paper text-xs px-2 py-0.5 tag-notch">-{product.discount_percent}%</span>
              </>
            )}
          </div>

          <p className="text-sm text-ink-soft mt-1 font-mono">SKU: {product.sku}</p>

          {/* Color */}
          {product.colors?.length > 0 && (
            <div className="mt-6">
              <p className="font-display uppercase text-sm tracking-widest2 mb-2">
                Color {selectedColor && `— ${product.colors.find((c) => c.id === selectedColor)?.name}`}
              </p>
              <div className="flex gap-2">
                {product.colors.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => { setSelectedColor(c.id); setSelectedSize(null); setActiveImage(0); }}
                    className={`w-9 h-9 rounded-full border-2 ${selectedColor === c.id ? 'border-signal' : 'border-transparent'}`}
                    style={{ backgroundColor: c.hex_code, boxShadow: '0 0 0 1px #D9D5CC' }}
                    title={c.name}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Size */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <p className="font-display uppercase text-sm tracking-widest2">Size</p>
              <button onClick={() => setSizeGuideOpen(true)} className="text-xs font-mono uppercase underline text-ink-soft">Size Guide</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {sizesForColor.map((v) => (
                <button
                  key={v.id}
                  disabled={v.stock === 0}
                  onClick={() => setSelectedSize(v.size.id)}
                  className={`w-12 h-12 text-xs font-mono border relative
                    ${selectedSize === v.size.id ? 'bg-ink text-paper border-ink' : 'border-line hover:border-ink'}
                    ${v.stock === 0 ? 'opacity-30 cursor-not-allowed line-through' : ''}`}
                >
                  {v.size.label}
                </button>
              ))}
            </div>
            {currentVariant && currentVariant.stock > 0 && currentVariant.stock <= 5 && (
              <p className="text-xs text-signal mt-2 font-mono">Only {currentVariant.stock} left</p>
            )}
          </div>

          {/* Add to bag / notify */}
          <div className="mt-8 flex flex-col gap-3">
            {currentVariant && currentVariant.stock === 0 ? (
              <div className="border border-line p-4">
                <p className="text-sm mb-2">This size is sold out.</p>
                {notifySent ? (
                  <p className="text-xs text-ink-soft font-mono">We'll email you when it's back.</p>
                ) : (
                  <div className="flex gap-2">
                    <input
                      value={notifyEmail}
                      onChange={(e) => setNotifyEmail(e.target.value)}
                      placeholder="Your email"
                      className="flex-1 border border-line px-3 py-2 text-sm outline-none"
                    />
                    <button onClick={handleNotify} className="bg-ink text-paper px-4 font-mono text-xs uppercase">Notify Me</button>
                  </div>
                )}
              </div>
            ) : (
              <button onClick={handleAddToBag} className="bg-ink text-paper py-4 font-display uppercase tracking-widest2 hover:bg-signal transition-colors">
                Add to Bag
              </button>
            )}
            {user && (
              <button className="border border-ink py-4 font-display uppercase tracking-widest2 flex items-center justify-center gap-2">
                <Heart size={16} /> Wishlist
              </button>
            )}
            {message && <p className="text-xs font-mono text-ink-soft">{message}</p>}
          </div>

          {/* Description */}
          <div className="mt-10 border-t border-line pt-6 space-y-4 text-sm">
            <p>{product.description}</p>
            <div className="grid grid-cols-2 gap-4 font-mono text-xs text-ink-soft">
              <div><span className="text-ink block">Material</span>{product.material}</div>
              <div><span className="text-ink block">Fit</span>{product.fit}</div>
            </div>
            <details className="border-t border-line pt-4">
              <summary className="font-display uppercase text-sm tracking-widest2 cursor-pointer">Care Instructions</summary>
              <p className="mt-2 text-ink-soft">{product.care_instructions}</p>
            </details>
          </div>
        </div>
      </div>

      {/* Reviews */}
      <section className="mt-20 border-t border-line pt-10">
        <h2 className="font-display text-2xl uppercase mb-6">Reviews</h2>
        {product.reviews.length === 0 ? (
          <p className="text-sm text-ink-soft">No reviews yet. Be the first to review this product.</p>
        ) : (
          <div className="space-y-6 max-w-2xl">
            {product.reviews.map((r) => (
              <div key={r.id} className="border-b border-line pb-4">
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((n) => <Star key={n} size={12} fill={n <= r.rating ? '#121212' : 'none'} />)}
                  {r.is_verified_purchase && <span className="text-[10px] font-mono uppercase text-ink-soft">Verified Purchase</span>}
                </div>
                {r.title && <p className="font-medium mt-1">{r.title}</p>}
                <p className="text-sm text-ink-soft mt-1">{r.comment}</p>
                <p className="text-xs font-mono text-ink-soft mt-1">{r.user_name}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Related */}
      {product.related_products?.length > 0 && (
        <section className="mt-20 border-t border-line pt-10">
          <h2 className="font-display text-2xl uppercase mb-6">You May Also Like</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-10">
            {product.related_products.slice(0, 4).map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </section>
      )}

      {sizeGuideOpen && (
        <div className="fixed inset-0 z-50 bg-ink/40 flex items-end md:items-center justify-center" onClick={() => setSizeGuideOpen(false)}>
          <div className="bg-paper max-w-lg w-full p-8" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-xl uppercase mb-4">Size Guide</h3>
            <table className="w-full text-sm font-mono">
              <thead><tr className="border-b border-ink text-left"><th className="py-2">Size</th><th>Chest</th><th>Waist</th><th>Length</th></tr></thead>
              <tbody>
                {[['S', '36"', '30"', '27"'], ['M', '38"', '32"', '28"'], ['L', '40"', '34"', '29"'], ['XL', '42"', '36"', '30"']].map((row) => (
                  <tr key={row[0]} className="border-b border-line">{row.map((cell, i) => <td key={i} className="py-2">{cell}</td>)}</tr>
                ))}
              </tbody>
            </table>
            <button onClick={() => setSizeGuideOpen(false)} className="mt-6 w-full bg-ink text-paper py-3 font-display uppercase tracking-widest2">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
