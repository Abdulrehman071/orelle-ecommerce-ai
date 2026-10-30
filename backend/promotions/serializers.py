from rest_framework import serializers
from .models import Coupon, Banner


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'placement', 'heading', 'subheading', 'message', 'image', 'cta_label', 'cta_url', 'order']
