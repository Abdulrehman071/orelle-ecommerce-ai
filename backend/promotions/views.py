from decimal import Decimal
from django.utils import timezone
from rest_framework import views, viewsets, status
from rest_framework.response import Response
from .models import Coupon, Banner
from .serializers import CouponValidateSerializer, BannerSerializer


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Banner.objects.filter(is_active=True)
    serializer_class = BannerSerializer
    filterset_fields = ['placement']


class ValidateCouponView(views.APIView):
    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        subtotal = serializer.validated_data['subtotal']
        try:
            coupon = Coupon.objects.get(code__iexact=code, is_active=True)
        except Coupon.DoesNotExist:
            return Response({'valid': False, 'detail': 'Invalid coupon code.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        if not (coupon.start_date <= now <= coupon.expiry_date):
            return Response({'valid': False, 'detail': 'This coupon has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        if subtotal < coupon.min_order_amount:
            return Response(
                {'valid': False, 'detail': f'Minimum order of PKR {coupon.min_order_amount} required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if coupon.discount_type == 'percentage':
            discount = subtotal * (coupon.value / Decimal('100'))
            if coupon.max_discount_amount:
                discount = min(discount, coupon.max_discount_amount)
        else:
            discount = coupon.value

        return Response({'valid': True, 'discount_amount': discount, 'code': coupon.code})
