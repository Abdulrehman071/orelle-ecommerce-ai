import { useEffect, useState, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { catalogApi } from '../api/endpoints';
import ProductCard from '../components/ProductCard';
import { SlidersHorizontal, X } from 'lucide-react';

const SORT_OPTIONS = [
  { value: '', label: 'Featured' },
  { value: 'newest', label: 'Newest' },
  { value: 'best_selling', label: 'Best Selling' },
  { value: 'price_low', label: 'Price: Low to High' },
  { value: 'price_high', label: 'Price: High to Low' },
  { value: 'discount', label: 'Discount' },
];

const FITS = ['slim', 'regular', 'relaxed', 'oversized'];

export default function CategoryPage() {
  const { department, categorySlug } = useParams();
  const [searchParams] = useSearchParams();
  const isSale = window.location.pathname === '/sale';
  const isNewIn = window.location.pathname === '/new-in';
  const searchQuery = searchParams.get('q');

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [sizes, setSizes] = useState([]);
  const [colors, setColors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [count, setCount] = useState(0);

  const [filters, setFilters] = useState({
    size: '', color: '', fit: '', min_price: '', max_price: '', sort: '',
  });

  useEffect(() => {
    catalogApi.sizes().then((res) => setSizes(res.data.results || res.data));
    catalogApi.colors().then((res) => setColors(res.data.results || res.data));
  }, []);

  useEffect(() => {
    if (department) {
      catalogApi.categories(department).then((res) => setCategories(res.data.results || res.data));
    }
  }, [department]);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (department) params.department = department;
    if (categorySlug) params.category = categorySlug;
    if (isSale) params.on_sale = true;
    if (isNewIn) params.is_new_arrival = true;
    if (searchQuery) params.search = searchQuery;
    Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });

    catalogApi.listProducts(params).then((res) => {
      setProducts(res.data.results || res.data);
      setCount(res.data.count ?? (res.data.results || res.data).length);
    }).finally(() => setLoading(false));
  }, [department, categorySlug, isSale, isNewIn, searchQuery, filters]);

  const title = useMemo(() => {
    if (searchQuery) return `Results for "${searchQuery}"`;
    if (isSale) return 'Sale';
    if (isNewIn) return 'New In';
    if (categorySlug) return categories.find((c) => c.slug === categorySlug)?.name || categorySlug;
    if (department) return department.charAt(0).toUpperCase() + department.slice(1);
    return 'All Products';
  }, [department, categorySlug, isSale, isNewIn, searchQuery, categories]);

  const setFilter = (key, value) => setFilters((f) => ({ ...f, [key]: f[key] === value ? '' : value }));
  const clearFilters = () => setFilters({ size: '', color: '', fit: '', min_price: '', max_price: '', sort: filters.sort });

  return (
    <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-10">
      <div className="mb-6">
        <h1 className="font-display text-3xl md:text-4xl uppercase tracking-wide">{title}</h1>
        <p className="text-ink-soft text-sm mt-1 font-mono">{count} Products</p>
      </div>

      {department && categories.length > 0 && !categorySlug && (
        <div className="flex flex-wrap gap-2 mb-8">
          {categories.map((c) => (
            <a key={c.id} href={`/category/${department}/${c.slug}`}
               className="text-xs font-mono uppercase border border-line px-3 py-1.5 hover:border-ink transition-colors">
              {c.name}
            </a>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between border-y border-line py-3 mb-6">
        <button onClick={() => setFiltersOpen(!filtersOpen)} className="flex items-center gap-2 font-display uppercase text-sm tracking-widest2">
          <SlidersHorizontal size={16} /> Filter
        </button>
        <select
          value={filters.sort}
          onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value }))}
          className="bg-transparent font-mono text-xs uppercase tracking-widest2 outline-none cursor-pointer"
        >
          {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <div className="flex gap-10">
        {filtersOpen && (
          <aside className="w-56 shrink-0 hidden md:block">
            <FilterPanel filters={filters} setFilter={setFilter} clearFilters={clearFilters} sizes={sizes} colors={colors} />
          </aside>
        )}

        {filtersOpen && (
          <div className="fixed inset-0 z-50 bg-paper md:hidden overflow-y-auto p-4">
            <div className="flex justify-between items-center mb-6">
              <span className="font-display uppercase text-lg">Filter</span>
              <button onClick={() => setFiltersOpen(false)}><X size={22} /></button>
            </div>
            <FilterPanel filters={filters} setFilter={setFilter} clearFilters={clearFilters} sizes={sizes} colors={colors} />
            <button onClick={() => setFiltersOpen(false)} className="w-full bg-ink text-paper py-3 font-display uppercase tracking-widest2 mt-6">
              Show {count} Results
            </button>
          </div>
        )}

        <div className="flex-1">
          {loading ? (
            <div className="text-center py-24 text-ink-soft font-mono text-sm">Loading products...</div>
          ) : products.length === 0 ? (
            <div className="text-center py-24 text-ink-soft font-mono text-sm">No products match these filters.</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-10">
              {products.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilterPanel({ filters, setFilter, clearFilters, sizes, colors }) {
  return (
    <div className="space-y-8">
      <div>
        <p className="font-display uppercase text-sm tracking-widest2 mb-3">Size</p>
        <div className="flex flex-wrap gap-2">
          {sizes.map((s) => (
            <button
              key={s.id}
              onClick={() => setFilter('size', s.label)}
              className={`w-10 h-10 text-xs font-mono border ${filters.size === s.label ? 'bg-ink text-paper border-ink' : 'border-line hover:border-ink'}`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="font-display uppercase text-sm tracking-widest2 mb-3">Color</p>
        <div className="flex flex-wrap gap-2">
          {colors.map((c) => (
            <button
              key={c.id}
              onClick={() => setFilter('color', c.name)}
              title={c.name}
              className={`w-8 h-8 rounded-full border-2 ${filters.color === c.name ? 'border-signal' : 'border-transparent'}`}
              style={{ backgroundColor: c.hex_code, boxShadow: '0 0 0 1px #D9D5CC' }}
            />
          ))}
        </div>
      </div>

      <div>
        <p className="font-display uppercase text-sm tracking-widest2 mb-3">Fit</p>
        <div className="flex flex-col gap-2 font-mono text-xs uppercase">
          {['slim', 'regular', 'relaxed', 'oversized'].map((f) => (
            <label key={f} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={filters.fit === f} onChange={() => setFilter('fit', f)} />
              {f}
            </label>
          ))}
        </div>
      </div>

      <div>
        <p className="font-display uppercase text-sm tracking-widest2 mb-3">Price (PKR)</p>
        <div className="flex gap-2">
          <input
            type="number" placeholder="Min"
            value={filters.min_price}
            onChange={(e) => setFilter('min_price', e.target.value)}
            className="w-full border border-line px-2 py-1.5 text-xs font-mono outline-none"
          />
          <input
            type="number" placeholder="Max"
            value={filters.max_price}
            onChange={(e) => setFilter('max_price', e.target.value)}
            className="w-full border border-line px-2 py-1.5 text-xs font-mono outline-none"
          />
        </div>
      </div>

      <button onClick={clearFilters} className="text-xs font-mono uppercase underline text-ink-soft">Clear all filters</button>
    </div>
  );
}
