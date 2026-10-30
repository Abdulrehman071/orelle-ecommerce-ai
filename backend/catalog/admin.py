from django.contrib import admin
from .models import (
    Category, Collection, Size, Color, Product, ProductImage,
    ProductVariant, Review, ReviewImage, BackInStockRequest
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'color', 'stock', 'variant_sku']
    readonly_fields = ['variant_sku']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price', 'sale_price', 'discount_percent', 'total_stock_display', 'is_active', 'is_new_arrival', 'is_featured']
    list_filter = ['category__department', 'category', 'is_active', 'is_new_arrival', 'is_featured', 'fit']
    search_fields = ['name', 'sku']
    inlines = [ProductImageInline, ProductVariantInline]
    list_editable = ['is_active', 'is_new_arrival', 'is_featured']

    def total_stock_display(self, obj):
        stock = obj.total_stock
        if stock == 0:
            return '⚠ SOLD OUT'
        if stock < 10:
            return f'⚠ Low: {stock}'
        return stock
    total_stock_display.short_description = 'Stock'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'parent', 'order']
    list_filter = ['department']
    list_editable = ['order']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_editable = ['is_active']


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['label', 'order']
    list_editable = ['order']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """Dedicated inventory management view - spec section 37"""
    list_display = ['product', 'size', 'color', 'stock', 'stock_status']
    list_filter = ['size', 'color', 'product__category']
    search_fields = ['product__name', 'variant_sku']
    list_editable = ['stock']

    def stock_status(self, obj):
        if obj.stock == 0:
            return '⚠ SOLD OUT'
        if obj.stock < 5:
            return '⚠ LOW STOCK'
        return 'In stock'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    list_editable = ['is_approved']


admin.site.register(ReviewImage)
admin.site.register(BackInStockRequest)
