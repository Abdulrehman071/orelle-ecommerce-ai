from django.contrib import admin
from .models import Order, OrderItem, Shipment, Payment, ReturnExchangeRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'size_label', 'color_name', 'unit_price', 'quantity']


class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin order management - spec section 39"""
    list_display = ['order_number', 'shipping_full_name', 'email', 'total', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'delivery_method']
    search_fields = ['order_number', 'email', 'phone', 'shipping_full_name']
    list_editable = ['status']
    inlines = [OrderItemInline, ShipmentInline, PaymentInline]
    readonly_fields = ['order_number', 'subtotal', 'shipping_fee', 'discount_amount', 'total']


@admin.register(ReturnExchangeRequest)
class ReturnExchangeAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'request_type', 'reason', 'status', 'created_at']
    list_filter = ['status', 'request_type', 'reason']
    list_editable = ['status']
