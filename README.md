# ORELLE — Fashion E-Commerce Platform

A full-stack fashion e-commerce platform (Men / Women / Juniors), built to the Phase 1 MVP spec:
Django REST Framework backend + React (Vite) storefront.

```
FRONTEND (React + Tailwind)
        │
        ▼
    REST API
        │
        ▼
BACKEND (Django + DRF)
        │
        ▼
   PostgreSQL / SQLite
```

## What's included (Phase 1 MVP)

- Men / Women / Juniors navigation, categories, collections
- Product listing with filters (size, color, price, fit, sale) and sorting
- Product detail: color/size selection with per-variant stock, image gallery, size guide, reviews, related products
- Cart + mini-cart drawer, Wishlist
- Guest checkout (account optional) with contact/shipping/delivery/payment steps
- Coupons (percentage/fixed, min order, expiry)
- Order confirmation + order tracking (by order number + email, or logged in)
- Customer accounts: register/login, order history, addresses
- Back-in-stock notifications
- Newsletter signup, store locator, static info pages
- Full Django admin: product & inventory management (with low-stock/sold-out flags), order management, coupon management, homepage banner management, customer management, review moderation

## Project structure

```
outfitters-clone/
├── backend/          Django REST API
│   ├── accounts/     Users, addresses
│   ├── catalog/      Categories, products, variants, sizes, colors, reviews
│   ├── cart/         Cart, wishlist
│   ├── orders/       Checkout, orders, returns/exchanges
│   ├── promotions/   Coupons, homepage banners
│   └── storefront/   Newsletter, notifications, store locations
└── frontend/         React storefront (Vite + Tailwind)
    └── src/
        ├── pages/        Home, Category, ProductDetail, Cart, Checkout, Account...
        ├── components/   Header, Footer, ProductCard, MiniCart
        ├── context/       Cart & Auth global state
        └── api/           API client
```

## Running it locally

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install django djangorestframework django-cors-headers django-filter pillow

python3 manage.py migrate
python3 manage.py seed_data      # populates ~66 sample products, categories, coupons, banners
python3 manage.py runserver 0.0.0.0:8000
```

Admin panel: http://localhost:8000/admin/
Login: `admin@outfitters.local` / `admin12345` (created by `seed_data`)

Sample coupons seeded: `SUMMER20` (20% off, min PKR 3,000), `WELCOME10` (10% off, first order).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Storefront: http://localhost:5173/
The frontend reads the API URL from `frontend/.env` (`VITE_API_URL`), defaulting to `http://localhost:8000/api`.

## What's next (Phase 2 / Phase 3, per the original spec)

- Real payment gateway integration (currently COD / Bank Transfer / Card are captured but not processed)
- Email/SMS/WhatsApp order notifications (models exist; sending isn't wired up)
- Product recommendation engine, recently viewed, complete-the-look
- Analytics dashboard
- Swap SQLite → PostgreSQL and add real product photography (current images are auto-generated placeholders)
- Deploy: Django behind gunicorn/nginx, React build served statically, environment-based secrets

## Notes

- This uses SQLite for zero-config local development. For production, switch `DATABASES` in `backend/config/settings.py` to PostgreSQL.
- Product images in the seed data are generated placeholder SVGs (colored panels with product/color labels) so you can see the variant-swapping and gallery behavior without needing real photography yet.
- CORS is wide open (`CORS_ALLOW_ALL_ORIGINS = True`) for local development — lock this down before deploying.

## AI Business Assistant (add-on)
A separate FastAPI service in `ai_service/` adds a multi-agent assistant (Customer Support, Sales Analytics, Marketing).
See `ai_service/README.md` for setup. Demo sales data: `python manage.py seed_sample_orders` (reverse with `--clear`).
