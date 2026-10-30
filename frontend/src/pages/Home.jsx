import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { catalogApi, promoApi } from '../api/endpoints';
import ProductCard from '../components/ProductCard';

const CATEGORY_TILES = [
  { label: 'Men', to: '/category/men', img: 'https://images.unsplash.com/photo-1516257984-b1b4d707412e?w=600&q=80' },
  { label: 'Women', to: '/category/women', img: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=80' },
  { label: 'Juniors', to: '/category/juniors', img: 'https://images.unsplash.com/photo-1503944583220-79d8926ad5e2?w=600&q=80' },
];

export default function Home() {
  const [hero, setHero] = useState(null);
  const [newArrivals, setNewArrivals] = useState([]);
  const [bestSellers, setBestSellers] = useState([]);

  useEffect(() => {
    promoApi.banners('hero').then((res) => setHero(res.data.results?.[0])).catch(() => {});
    catalogApi.newArrivals().then((res) => setNewArrivals(res.data)).catch(() => {});
    catalogApi.bestSellers().then((res) => setBestSellers(res.data)).catch(() => {});
  }, []);

  return (
    <div>
      {/* Hero */}
      <section className="relative h-[78vh] min-h-[480px] flex items-end bg-ink text-paper overflow-hidden">
        <div
          className="absolute inset-0 opacity-70 bg-cover bg-center"
          style={{ backgroundImage: "url('https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1600&q=80')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/20 to-transparent" />
        <div className="relative z-10 max-w-[1400px] mx-auto px-4 md:px-8 pb-14 w-full">
          <p className="font-mono text-xs tracking-widest2 uppercase text-paper/70 mb-3">Season 26 / Drop 01</p>
          <h1 className="font-display text-5xl md:text-7xl uppercase leading-[0.95] mb-6 max-w-3xl">
            {hero?.heading || "SUMMER '26 COLLECTION"}
          </h1>
          <p className="text-paper/80 mb-8 max-w-md">{hero?.subheading || 'Discover the new collection.'}</p>
          <div className="flex gap-4">
            <Link to="/category/men" className="bg-paper text-ink px-6 py-3 font-display uppercase tracking-widest2 text-sm hover:bg-signal hover:text-paper transition-colors">
              Shop Men
            </Link>
            <Link to="/category/women" className="border border-paper px-6 py-3 font-display uppercase tracking-widest2 text-sm hover:bg-paper hover:text-ink transition-colors">
              Shop Women
            </Link>
          </div>
        </div>
      </section>

      {/* Shop by department */}
      <section className="max-w-[1400px] mx-auto px-4 md:px-8 py-16">
        <div className="flex items-baseline justify-between mb-8">
          <h2 className="font-display text-2xl uppercase tracking-wide">Shop the Department</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {CATEGORY_TILES.map((tile) => (
            <Link key={tile.label} to={tile.to} className="group relative aspect-[3/4] overflow-hidden block">
              <img src={tile.img} alt={tile.label} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
              <div className="absolute inset-0 bg-gradient-to-t from-ink/70 to-transparent" />
              <span className="absolute bottom-6 left-6 font-display text-3xl uppercase text-paper tracking-wide">{tile.label}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* New Arrivals */}
      {newArrivals.length > 0 && (
        <section className="max-w-[1400px] mx-auto px-4 md:px-8 py-16">
          <div className="flex items-baseline justify-between mb-8">
            <h2 className="font-display text-2xl uppercase tracking-wide">New Arrivals</h2>
            <Link to="/new-in" className="font-mono text-xs uppercase tracking-widest2 border-b border-ink pb-0.5">View All</Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-10">
            {newArrivals.slice(0, 8).map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </section>
      )}

      {/* Best Sellers */}
      {bestSellers.length > 0 && (
        <section className="max-w-[1400px] mx-auto px-4 md:px-8 py-16">
          <div className="flex items-baseline justify-between mb-8">
            <h2 className="font-display text-2xl uppercase tracking-wide">Best Sellers</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-10">
            {bestSellers.slice(0, 8).map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </section>
      )}

      {/* Sale strip */}
      <section className="bg-signal text-paper py-20 text-center my-16">
        <p className="font-mono text-xs tracking-widest2 uppercase mb-2">Up to 50% off</p>
        <h2 className="font-display text-4xl md:text-6xl uppercase mb-6">The Sale</h2>
        <Link to="/sale" className="inline-block bg-paper text-ink px-8 py-3 font-display uppercase tracking-widest2 text-sm">
          Shop Sale
        </Link>
      </section>
    </div>
  );
}
