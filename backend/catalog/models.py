import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Department(models.TextChoices):
    MEN = 'men', 'Men'
    WOMEN = 'women', 'Women'
    JUNIORS = 'juniors', 'Juniors'


class Category(models.Model):
    """e.g. Men > Shirts, Women > Dresses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    department = models.CharField(max_length=10, choices=Department.choices)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.department}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_department_display()} / {self.name}"


class Collection(models.Model):
    """e.g. Summer Collection, Essentials, Streetwear - spec section 31"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    banner_image = models.ImageField(upload_to='collections/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Size(models.Model):
    label = models.CharField(max_length=10, unique=True)  # XS, S, M, L, XL, XXL
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.label


class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, default='#000000')

    def __str__(self):
        return self.name


class Fit(models.TextChoices):
    SLIM = 'slim', 'Slim Fit'
    REGULAR = 'regular', 'Regular Fit'
    RELAXED = 'relaxed', 'Relaxed Fit'
    OVERSIZED = 'oversized', 'Oversized'


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    collections = models.ManyToManyField(Collection, blank=True, related_name='products')

    description = models.TextField(blank=True)
    material = models.CharField(max_length=200, blank=True)
    fit = models.CharField(max_length=10, choices=Fit.choices, default=Fit.REGULAR)
    care_instructions = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_new_arrival = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    # best_seller is computed from OrderItem sales, see `annotate_best_sellers` manager method

    video_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200] + '-' + str(self.sku).lower()
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.sale_price and self.price > 0:
            return round((1 - (self.sale_price / self.price)) * 100)
        return 0

    @property
    def current_price(self):
        return self.sale_price if self.sale_price else self.price

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    @property
    def average_rating(self):
        agg = self.reviews.filter(is_approved=True).aggregate(models.Avg('rating'))
        return round(agg['rating__avg'] or 0, 1)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    class ImageType(models.TextChoices):
        MAIN = 'main', 'Main'
        FRONT = 'front', 'Front'
        BACK = 'back', 'Back'
        SIDE = 'side', 'Side'
        MODEL = 'model', 'Model'
        CLOSEUP = 'closeup', 'Close-up'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True,
                               help_text='If set, this image only shows when this color is selected')
    image = models.ImageField(upload_to='products/')
    image_type = models.CharField(max_length=10, choices=ImageType.choices, default=ImageType.MAIN)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} - {self.image_type}"


class ProductVariant(models.Model):
    """A specific size+color combination of a product, with its own stock (spec section 13-14)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    color = models.ForeignKey(Color, on_delete=models.PROTECT)
    stock = models.PositiveIntegerField(default=0)
    variant_sku = models.CharField(max_length=60, unique=True, blank=True)

    class Meta:
        unique_together = ('product', 'size', 'color')

    def save(self, *args, **kwargs):
        if not self.variant_sku:
            self.variant_sku = f"{self.product.sku}-{self.color.name[:3].upper()}-{self.size.label}"
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock > 0

    def __str__(self):
        return f"{self.product.name} / {self.color.name} / {self.size.label} ({self.stock})"


class BackInStockRequest(models.Model):
    """spec section 45"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='notify_requests')
    email = models.EmailField()
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('variant', 'email')


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=150, blank=True)
    comment = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.rating}★ by {self.user}"


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='reviews/')
