import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { cartApi } from '../api/endpoints';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const [cart, setCart] = useState({ items: [], subtotal: 0, total_items: 0 });
  const [loading, setLoading] = useState(false);
  const [miniCartOpen, setMiniCartOpen] = useState(false);

  const refreshCart = useCallback(async () => {
    try {
      const res = await cartApi.get();
      setCart(res.data);
    } catch (e) {
      console.error('Failed to load cart', e);
    }
  }, []);

  useEffect(() => {
    refreshCart();
  }, [refreshCart]);

  const addItem = async (variantId, quantity = 1) => {
    setLoading(true);
    try {
      const res = await cartApi.addItem(variantId, quantity);
      setCart(res.data);
      setMiniCartOpen(true);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.response?.data?.detail || 'Could not add to bag.' };
    } finally {
      setLoading(false);
    }
  };

  const updateItem = async (itemId, quantity) => {
    const res = await cartApi.updateItem(itemId, quantity);
    setCart(res.data);
  };

  const removeItem = async (itemId) => {
    const res = await cartApi.removeItem(itemId);
    setCart(res.data);
  };

  return (
    <CartContext.Provider value={{ cart, loading, addItem, updateItem, removeItem, refreshCart, miniCartOpen, setMiniCartOpen }}>
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => useContext(CartContext);
