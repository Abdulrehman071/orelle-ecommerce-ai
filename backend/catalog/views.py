from django.db.models import Count, Q
from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, filters as df_filters

from .models import Category, Collection, Product, Size, Color, Review, BackInStockRequest
from .serializers import (
    CategorySerializer, CollectionSerializer, SizeSerializer, ColorSerializer,
    ProductListSerializer, ProductDetailSerializer, ReviewSerializer,
    BackInStockRequestSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ['department', 'parent']


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Collection.objects.filter(is_active=True)
    serializer_class = CollectionSerializer
    lookup_field = 'slug'


class SizeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer


class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer


class ProductFilter(FilterSet):
    department = df_filters.CharFilter(field_name='category__department')
    category = df_filters.CharFilter(field_name='category__slug')
    collection = df_filters.CharFilter(field_name='collections__slug')
    size = df_filters.CharFilter(field_name='variants__size__label')
    color = df_filters.CharFilter(field_name='variants__color__name')
    fit = df_filters.CharFilter(field_name='fit')
    min_price = df_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = df_filters.NumberFilter(field_name='price', lookup_expr='lte')
    on_sale = df_filters.BooleanFilter(method='filter_on_sale')

    class Meta:
        model = Product
        fields = ['department', 'category', 'collection', 'size', 'color', 'fit', 'is_new_arrival', 'is_featured']

    def filter_on_sale(self, qs, name, value):
        return qs.filter(sale_price__isnull=False) if value else qs


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).prefetch_related(
        'images', 'variants__size', 'variants__color', 'reviews'
    ).distinct()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'description', 'category__name']
    ordering_fields = ['price', 'created_at']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        qs = super().get_queryset()
        sort = self.request.query_params.get('sort')
        if sort == 'newest':
            qs = qs.order_by('-created_at')
        elif sort == 'price_low':
            qs = qs.order_by('price')
        elif sort == 'price_high':
            qs = qs.order_by('-price')
        elif sort == 'discount':
            qs = qs.order_by('-sale_price')
        elif sort in ('best_selling', 'most_popular'):
            qs = qs.annotate(sold=Count('variants__orderitem')).order_by('-sold')
        return qs

    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        qs = self.get_queryset().filter(is_new_arrival=True)[:12]
        return Response(ProductListSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def best_sellers(self, request):
        qs = self.get_queryset().annotate(sold=Count('variants__orderitem')).order_by('-sold')[:12]
        return Response(ProductListSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def on_sale(self, request):
        qs = self.get_queryset().filter(sale_price__isnull=False)
        return Response(ProductListSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def search_suggestions(self, request):
        q = request.query_params.get('q', '')
        if len(q) < 2:
            return Response([])
        qs = self.get_queryset().filter(Q(name__icontains=q) | Q(category__name__icontains=q))[:6]
        return Response(ProductListSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_review(self, request, slug=None):
        product = self.get_object()
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BackInStockRequestViewSet(viewsets.ModelViewSet):
    queryset = BackInStockRequest.objects.all()
    serializer_class = BackInStockRequestSerializer
    http_method_names = ['post']
