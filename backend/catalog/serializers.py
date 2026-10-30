from rest_framework import serializers
from .models import (
    Category, Collection, Size, Color, Product, ProductImage,
    ProductVariant, Review, BackInStockRequest
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'department', 'parent', 'order']


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id', 'name', 'slug', 'description', 'banner_image', 'is_active']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'label', 'order']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code']


class ProductImageSerializer(serializers.ModelSerializer):
    color = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_type', 'color', 'order']


class ProductVariantSerializer(serializers.ModelSerializer):
    size = SizeSerializer(read_only=True)
    color = ColorSerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'color', 'stock', 'in_stock', 'variant_sku']


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user_name', 'rating', 'title', 'comment', 'is_verified_purchase', 'created_at']

    def get_user_name(self, obj):
        return obj.user.first_name or obj.user.username


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for grids: category/product listing, homepage sections."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    department = serializers.CharField(source='category.department', read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    main_image = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category_name', 'department',
            'price', 'sale_price', 'current_price', 'discount_percent',
            'is_new_arrival', 'is_featured', 'main_image', 'colors', 'in_stock',
            'average_rating',
        ]

    def get_main_image(self, obj):
        img = obj.images.filter(image_type='main').first() or obj.images.first()
        if img and img.image:
            request = self.context.get('request')
            url = img.image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_colors(self, obj):
        colors = {v.color_id: v.color for v in obj.variants.all()}
        return ColorSerializer(colors.values(), many=True).data

    def get_in_stock(self, obj):
        return obj.total_stock > 0


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    collections = CollectionSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    sizes = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'category', 'collections',
            'description', 'material', 'fit', 'care_instructions',
            'price', 'sale_price', 'current_price', 'discount_percent',
            'is_new_arrival', 'is_featured', 'video_url',
            'images', 'variants', 'sizes', 'colors', 'reviews',
            'average_rating', 'related_products',
        ]

    def get_images(self, obj):
        request = self.context.get('request')
        return ProductImageSerializer(obj.images.all(), many=True, context={'request': request}).data

    def get_sizes(self, obj):
        sizes = {v.size_id: v.size for v in obj.variants.all()}
        return SizeSerializer(sizes.values(), many=True).data

    def get_colors(self, obj):
        colors = {v.color_id: v.color for v in obj.variants.all()}
        return ColorSerializer(colors.values(), many=True).data

    def get_related_products(self, obj):
        related = Product.objects.filter(category=obj.category, is_active=True).exclude(id=obj.id)[:8]
        return ProductListSerializer(related, many=True, context=self.context).data


class BackInStockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackInStockRequest
        fields = ['id', 'variant', 'email']
