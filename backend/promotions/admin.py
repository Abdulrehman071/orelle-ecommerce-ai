from django.contrib import admin
from .models import Coupon, CouponUsage, Banner


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Discount management - spec section 41"""
    list_display = ['code', 'discount_type', 'value', 'min_order_amount', 'usage_limit', 'expiry_date', 'is_active', 'status']
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']

    def status(self, obj):
        from django.utils import timezone
        return 'Active' if obj.is_active and obj.expiry_date > timezone.now() else 'Expired'


admin.site.register(CouponUsage)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """Homepage management - spec section 42"""
    list_display = ['placement', 'heading', 'message', 'is_active', 'order']
    list_filter = ['placement', 'is_active']
    list_editable = ['is_active', 'order']
