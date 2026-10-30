from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, views, status, permissions, mixins
from rest_framework.response import Response
from cart.views import get_or_create_cart
from cart.models import CartItem
from promotions.models import Coupon, CouponUsage
from .models import Order, OrderItem, Shipment, Payment, ReturnExchangeRequest
from .serializers import OrderSerializer, CheckoutSerializer, ReturnExchangeRequestSerializer

STANDARD_SHIPPING_FEE = Decimal('250')
EXPRESS_SHIPPING_FEE = Decimal('600')
FREE_SHIPPING_THRESHOLD = Decimal('5000')


class CheckoutView(views.APIView):
    """Creates an Order from the current cart: spec section 19-20."""

    def post(self, request):
        cart = get_or_create_cart(request)
        items = list(cart.items.filter(saved_for_later=False))
        if not items:
            return Response({'detail': 'Your bag is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # validate stock
        for item in items:
            if item.variant.stock < item.quantity:
                return Response(
                    {'detail': f'{item.variant.product.name} ({item.variant.size.label}) no longer has enough stock.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        subtotal = sum(i.line_total for i in items)
        shipping_fee = Decimal('0') if subtotal >= FREE_SHIPPING_THRESHOLD else (
            EXPRESS_SHIPPING_FEE if data['delivery_method'] == 'express' else STANDARD_SHIPPING_FEE
        )

        discount_amount = Decimal('0')
        coupon = None
        coupon_code = data.get('coupon_code', '')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
                now = timezone.now()
                if coupon.start_date <= now <= coupon.expiry_date and subtotal >= coupon.min_order_amount:
                    if coupon.discount_type == 'percentage':
                        discount_amount = subtotal * (coupon.value / Decimal('100'))
                        if coupon.max_discount_amount:
                            discount_amount = min(discount_amount, coupon.max_discount_amount)
                    else:
                        discount_amount = coupon.value
                else:
                    coupon = None
            except Coupon.DoesNotExist:
                coupon = None

        total = subtotal + shipping_fee - discount_amount

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                email=data['email'],
                phone=data['phone'],
                shipping_full_name=data['shipping_full_name'],
                shipping_address=data['shipping_address'],
                shipping_city=data['shipping_city'],
                shipping_province=data['shipping_province'],
                shipping_postal_code=data.get('shipping_postal_code', ''),
                delivery_method=data['delivery_method'],
                payment_method=data['payment_method'],
                subtotal=subtotal,
                shipping_fee=shipping_fee,
                discount_amount=discount_amount,
                total=total,
                coupon_code=coupon_code if coupon else '',
                status=Order.Status.PLACED,
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    size_label=item.variant.size.label,
                    color_name=item.variant.color.name,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                )
                item.variant.stock -= item.quantity
                item.variant.save()

            Shipment.objects.create(
                order=order,
                estimated_delivery_days='2-4' if data['delivery_method'] == 'express' else '5-7',
            )
            Payment.objects.create(order=order, method=data['payment_method'], status=Payment.Status.PENDING)

            if coupon and request.user.is_authenticated:
                CouponUsage.objects.create(coupon=coupon, user=request.user, order=order)

            items_qs = CartItem.objects.filter(cart=cart, saved_for_later=False)
            items_qs.delete()

        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}


class GuestOrderLookupView(views.APIView):
    """Allow tracking an order without login via order_number + email (spec section 21)."""

    def get(self, request):
        order_number = request.query_params.get('order_number')
        email = request.query_params.get('email')
        try:
            order = Order.objects.get(order_number=order_number, email__iexact=email)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order, context={'request': request}).data)


class ReturnExchangeViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ReturnExchangeRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReturnExchangeRequest.objects.filter(order_item__order__user=self.request.user)
