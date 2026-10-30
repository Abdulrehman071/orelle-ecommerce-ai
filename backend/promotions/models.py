import uuid
from django.conf import settings
from django.db import models


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED = 'fixed', 'Fixed Amount'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    applicable_categories = models.ManyToManyField('catalog.Category', blank=True)
    applicable_products = models.ManyToManyField('catalog.Product', blank=True)

    is_first_order_only = models.BooleanField(default=False)
    is_user_specific = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='exclusive_coupons')

    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)


class Banner(models.Model):
    """Homepage hero / promo banners, admin-editable (spec sections 3-4, 42)"""
    class Placement(models.TextChoices):
        HERO = 'hero', 'Hero Banner'
        ANNOUNCEMENT = 'announcement', 'Announcement Bar'
        SALE = 'sale', 'Sale Banner'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    placement = models.CharField(max_length=20, choices=Placement.choices)
    heading = models.CharField(max_length=200, blank=True)
    subheading = models.CharField(max_length=300, blank=True)
    message = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to='banners/', blank=True, null=True)
    cta_label = models.CharField(max_length=50, blank=True)
    cta_url = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.placement}: {self.heading or self.message}"
