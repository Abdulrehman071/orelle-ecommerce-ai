from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from catalog.views import (
    CategoryViewSet, CollectionViewSet, SizeViewSet, ColorViewSet,
    ProductViewSet, BackInStockRequestViewSet,
)
from cart.views import CartView, CartItemView, WishlistView
from accounts.views import RegisterView, LoginView, LogoutView, ProfileView, AddressViewSet
from orders.views import CheckoutView, OrderViewSet, GuestOrderLookupView, ReturnExchangeViewSet
from promotions.views import BannerViewSet, ValidateCouponView
from storefront.views import NewsletterSubscribeView, StoreLocationViewSet, NotificationViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet)
router.register('collections', CollectionViewSet)
router.register('sizes', SizeViewSet)
router.register('colors', ColorViewSet)
router.register('products', ProductViewSet)
router.register('back-in-stock', BackInStockRequestViewSet)
router.register('addresses', AddressViewSet, basename='address')
router.register('orders', OrderViewSet, basename='order')
router.register('returns', ReturnExchangeViewSet, basename='return')
router.register('banners', BannerViewSet)
router.register('newsletter', NewsletterSubscribeView, basename='newsletter')
router.register('stores', StoreLocationViewSet)
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/profile/', ProfileView.as_view()),
    path('api/cart/', CartView.as_view()),
    path('api/cart/items/', CartItemView.as_view()),
    path('api/cart/items/<uuid:item_id>/', CartItemView.as_view()),
    path('api/wishlist/', WishlistView.as_view()),
    path('api/wishlist/<uuid:product_id>/', WishlistView.as_view()),
    path('api/checkout/', CheckoutView.as_view()),
    path('api/orders/track/', GuestOrderLookupView.as_view()),
    path('api/coupons/validate/', ValidateCouponView.as_view()),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
