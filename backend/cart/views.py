from rest_framework import views, status, permissions
from rest_framework.response import Response
from catalog.models import ProductVariant
from .models import Cart, CartItem, Wishlist, WishlistItem
from .serializers import CartSerializer, CartItemSerializer, WishlistSerializer


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key, user=None)
    return cart


class CartView(views.APIView):
    def get(self, request):
        cart = get_or_create_cart(request)
        return Response(CartSerializer(cart, context={'request': request}).data)


class CartItemView(views.APIView):
    def post(self, request):
        """Add item to cart. Body: {variant_id, quantity}"""
        cart = get_or_create_cart(request)
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        variant = ProductVariant.objects.get(id=variant_id)

        if variant.stock < quantity:
            return Response({'detail': 'Not enough stock available.'}, status=status.HTTP_400_BAD_REQUEST)

        item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={'quantity': quantity})
        if not created:
            item.quantity += quantity
            item.save()
        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def patch(self, request, item_id=None):
        """Update quantity of a cart item"""
        cart = get_or_create_cart(request)
        item = CartItem.objects.get(id=item_id, cart=cart)
        quantity = int(request.data.get('quantity', item.quantity))
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return Response(CartSerializer(cart, context={'request': request}).data)

    def delete(self, request, item_id=None):
        cart = get_or_create_cart(request)
        CartItem.objects.filter(id=item_id, cart=cart).delete()
        return Response(CartSerializer(cart, context={'request': request}).data)


class WishlistView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        return Response(WishlistSerializer(wishlist, context={'request': request}).data)

    def post(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        WishlistItem.objects.get_or_create(wishlist=wishlist, product_id=product_id)
        return Response(WishlistSerializer(wishlist, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def delete(self, request, product_id=None):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).delete()
        return Response(WishlistSerializer(wishlist, context={'request': request}).data)
