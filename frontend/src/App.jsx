import { Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import MiniCart from './components/MiniCart';
import Home from './pages/Home';
import CategoryPage from './pages/CategoryPage';
import ProductDetail from './pages/ProductDetail';
import CartPage from './pages/CartPage';
import WishlistPage from './pages/WishlistPage';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import CheckoutPage from './pages/CheckoutPage';
import OrderConfirmation from './pages/OrderConfirmation';
import TrackOrderPage from './pages/TrackOrderPage';
import AccountPage from './pages/AccountPage';
import InfoPage from './pages/InfoPage';
import StoreLocator from './pages/StoreLocator';
import AssistantConsole from './pages/AssistantConsole';
import AssistantWidget from './components/AssistantWidget';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col font-body">
      <ScrollToTop />
      <Header />
      <MiniCart />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/category/:department" element={<CategoryPage />} />
          <Route path="/category/:department/:categorySlug" element={<CategoryPage />} />
          <Route path="/new-in" element={<CategoryPage />} />
          <Route path="/sale" element={<CategoryPage />} />
          <Route path="/search" element={<CategoryPage />} />
          <Route path="/product/:slug" element={<ProductDetail />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/wishlist" element={<WishlistPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-confirmation/:orderNumber" element={<OrderConfirmation />} />
          <Route path="/track-order" element={<TrackOrderPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/stores" element={<StoreLocator />} />
          <Route path="/assistant" element={<AssistantConsole />} />
          <Route path="/info/:page" element={<InfoPage />} />
        </Routes>
      </main>
      <Footer />
      <AssistantWidget />
    </div>
  );
}
