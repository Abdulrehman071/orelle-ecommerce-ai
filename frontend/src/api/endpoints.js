import api from './client';

export const catalogApi = {
  listProducts: (params) => api.get('/products/', { params }),
  getProduct: (slug) => api.get(`/products/${slug}/`),
  newArrivals: () => api.get('/products/new_arrivals/'),
  bestSellers: () => api.get('/products/best_sellers/'),
  onSale: () => api.get('/products/on_sale/'),
  searchSuggestions: (q) => api.get('/products/search_suggestions/', { params: { q } }),
  addReview: (slug, data) => api.post(`/products/${slug}/add_review/`, data),
  categories: (department) => api.get('/categories/', { params: department ? { department } : {} }),
  collections: () => api.get('/collections/'),
  sizes: () => api.get('/sizes/'),
  colors: () => api.get('/colors/'),
  notifyBackInStock: (variantId, email) => api.post('/back-in-stock/', { variant: variantId, email }),
};

export const cartApi = {
  get: () => api.get('/cart/'),
  addItem: (variant_id, quantity = 1) => api.post('/cart/items/', { variant_id, quantity }),
  updateItem: (itemId, quantity) => api.patch(`/cart/items/${itemId}/`, { quantity }),
  removeItem: (itemId) => api.delete(`/cart/items/${itemId}/`),
};

export const wishlistApi = {
  get: () => api.get('/wishlist/'),
  add: (product_id) => api.post('/wishlist/', { product_id }),
  remove: (productId) => api.delete(`/wishlist/${productId}/`),
};

export const authApi = {
  register: (data) => api.post('/auth/register/', data),
  login: (data) => api.post('/auth/login/', data),
  logout: () => api.post('/auth/logout/'),
  profile: () => api.get('/auth/profile/'),
  updateProfile: (data) => api.patch('/auth/profile/', data),
};

export const addressApi = {
  list: () => api.get('/addresses/'),
  create: (data) => api.post('/addresses/', data),
  update: (id, data) => api.patch(`/addresses/${id}/`, data),
  remove: (id) => api.delete(`/addresses/${id}/`),
};

export const orderApi = {
  checkout: (data) => api.post('/checkout/', data),
  myOrders: () => api.get('/orders/'),
  detail: (orderNumber) => api.get(`/orders/${orderNumber}/`),
  guestTrack: (orderNumber, email) => api.get('/orders/track/', { params: { order_number: orderNumber, email } }),
};

export const promoApi = {
  banners: (placement) => api.get('/banners/', { params: placement ? { placement } : {} }),
  validateCoupon: (code, subtotal) => api.post('/coupons/validate/', { code, subtotal }),
};

export const storefrontApi = {
  subscribeNewsletter: (email) => api.post('/newsletter/', { email }),
  stores: (city) => api.get('/stores/', { params: city ? { city } : {} }),
};
