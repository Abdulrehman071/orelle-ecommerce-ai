import { useEffect, useState } from 'react';
import { storefrontApi } from '../api/endpoints';

export default function StoreLocator() {
  const [stores, setStores] = useState([]);

  useEffect(() => {
    storefrontApi.stores().then((res) => setStores(res.data.results || res.data));
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="font-display text-3xl uppercase mb-8">Find a Store</h1>
      <div className="space-y-6">
        {stores.map((s) => (
          <div key={s.id} className="border border-line p-5">
            <h3 className="font-display uppercase text-lg">{s.name}</h3>
            <p className="text-sm text-ink-soft mt-1">{s.address}, {s.city}</p>
            <p className="text-sm font-mono mt-2">{s.phone}</p>
            <p className="text-xs text-ink-soft font-mono mt-1">{s.opening_hours}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
