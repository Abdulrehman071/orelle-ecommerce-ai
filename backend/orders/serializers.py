from rest_framework import serializers
from .models import Order, OrderItem, Shipment, ReturnExchangeRequest


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_slug = serializers.CharField(source='variant.product.slug', read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_slug', 'product_image', 'size_label', 'color_name', 'unit_price', 'quantity', 'line_total']

    def get_product_image(self, obj):
        img = obj.variant.product.images.first()
        if img and img.image:
            request = self.context.get('request')
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ['carrier', 'tracking_number', 'shipped_at', 'delivered_at', 'estimated_delivery_days']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipment = ShipmentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'email', 'phone',
            'shipping_full_name', 'shipping_address', 'shipping_city', 'shipping_province', 'shipping_postal_code',
            'delivery_method', 'payment_method',
            'subtotal', 'shipping_fee', 'discount_amount', 'total', 'coupon_code',
            'status', 'items', 'shipment', 'created_at',
        ]
        read_only_fields = ['order_number', 'subtotal', 'shipping_fee', 'discount_amount', 'total', 'status']


class CheckoutSerializer(serializers.Serializer):
    """Input payload for placing an order from the current cart."""
    email = serializers.EmailField()
    phone = serializers.CharField()
    shipping_full_name = serializers.CharField()
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField()
    shipping_province = serializers.CharField()
    shipping_postal_code = serializers.CharField(required=False, allow_blank=True)
    delivery_method = serializers.ChoiceField(choices=Order.DeliveryMethod.choices, default=Order.DeliveryMethod.STANDARD)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices, default=Order.PaymentMethod.COD)
    coupon_code = serializers.CharField(required=False, allow_blank=True)


class ReturnExchangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnExchangeRequest
        fields = ['id', 'order_item', 'request_type', 'reason', 'notes', 'status', 'created_at']
        read_only_fields = ['status']
