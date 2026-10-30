import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model
from catalog.models import Category, Collection, Size, Color, Product, ProductImage, ProductVariant, Review
from promotions.models import Coupon, Banner
from storefront.models import StoreLocation

User = get_user_model()

MEN_CATEGORIES = ['T-Shirts', 'Polos', 'Shirts', 'Jeans', 'Trousers', 'Hoodies', 'Footwear']
WOMEN_CATEGORIES = ['T-Shirts', 'Shirts', 'Dresses', 'Jeans', 'Trousers', 'Footwear', 'Bags']
JUNIOR_CATEGORIES = ['T-Shirts', 'Shirts', 'Jeans', 'Footwear', 'Accessories']

COLORS = [('Black', '#111111'), ('White', '#F5F5F5'), ('Navy', '#1B2A4A'), ('Brown', '#5C4033'),
          ('Olive', '#5F6B3F'), ('Red', '#B22222'), ('Grey', '#8A8A8A'), ('Beige', '#D8C7A1')]
SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

PRODUCT_NAME_TEMPLATES = {
    'T-Shirts': ['Essential Crew Neck Tee', 'Oversized Graphic Tee', 'Ribbed Slim Tee', 'Pocket Tee'],
    'Polos': ['Classic Pique Polo', 'Slim Fit Polo', 'Textured Knit Polo'],
    'Shirts': ['Relaxed Fit Shirt', 'Linen Blend Shirt', 'Oxford Button-Down', 'Printed Resort Shirt'],
    'Jeans': ['Slim Tapered Jeans', 'Straight Fit Jeans', 'Relaxed Denim', 'Distressed Denim'],
    'Trousers': ['Tailored Chino', 'Wide Leg Trouser', 'Cargo Trouser'],
    'Hoodies': ['Fleece Pullover Hoodie', 'Oversized Hoodie', 'Zip-Up Hoodie'],
    'Footwear': ['Canvas Low-Top Sneaker', 'Chunky Trainer', 'Leather Loafer'],
    'Dresses': ['Wrap Midi Dress', 'Floral Sundress', 'Shirt Dress'],
    'Bags': ['Structured Tote', 'Crossbody Bag', 'Canvas Backpack'],
    'Accessories': ['Woven Cap', 'Canvas Belt', 'Printed Bandana'],
}

FIT_CHOICES = ['slim', 'regular', 'relaxed', 'oversized']


def make_placeholder_svg(text, bg):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
<rect width="800" height="1000" fill="{bg}"/>
<text x="400" y="500" font-family="Helvetica, sans-serif" font-size="34" fill="#ffffff"
text-anchor="middle" dominant-baseline="middle" opacity="0.85">{text}</text>
</svg>'''
    return svg.encode('utf-8')


class Command(BaseCommand):
    help = 'Seed database with sample fashion catalog data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding sizes and colors...')
        sizes = {}
        for i, label in enumerate(SIZES):
            sizes[label], _ = Size.objects.get_or_create(label=label, defaults={'order': i})

        colors = {}
        for name, hexcode in COLORS:
            colors[name], _ = Color.objects.get_or_create(name=name, defaults={'hex_code': hexcode})

        self.stdout.write('Seeding categories...')
        cat_map = {}
        for dept, cats in [('men', MEN_CATEGORIES), ('women', WOMEN_CATEGORIES), ('juniors', JUNIOR_CATEGORIES)]:
            for order, cat_name in enumerate(cats):
                cat, _ = Category.objects.get_or_create(name=cat_name, department=dept, defaults={'order': order})
                cat_map[(dept, cat_name)] = cat

        self.stdout.write('Seeding collections...')
        collections = {}
        for name in ['Summer Collection', 'Essentials', 'New Collection', 'Streetwear', 'Formal']:
            collections[name], _ = Collection.objects.get_or_create(name=name)

        self.stdout.write('Seeding products (this may take a moment)...')
        sku_counter = 1000
        products_created = []
        for dept, cats in [('men', MEN_CATEGORIES), ('women', WOMEN_CATEGORIES), ('juniors', JUNIOR_CATEGORIES)]:
            for cat_name in cats:
                cat = cat_map[(dept, cat_name)]
                templates = PRODUCT_NAME_TEMPLATES.get(cat_name, [f'{cat_name} Item'])
                for name in templates:
                    sku_counter += 1
                    price = random.choice([1990, 2490, 2990, 3490, 3990, 4990, 5990, 6990, 8990])
                    on_sale = random.random() < 0.35
                    sale_price = round(price * random.choice([0.5, 0.6, 0.7, 0.8]), -1) if on_sale else None
                    is_new = random.random() < 0.3
                    is_featured = random.random() < 0.25

                    product = Product.objects.create(
                        name=f"{name}",
                        sku=f"OF-{sku_counter}",
                        category=cat,
                        description=(
                            f"A wardrobe staple reimagined. The {name.lower()} is built from "
                            f"breathable, durable fabric designed for everyday wear, with a fit "
                            f"and finish that holds up wash after wash."
                        ),
                        material=random.choice(['100% Cotton', 'Cotton Blend', 'Denim', 'Polyester Blend', 'Linen Cotton']),
                        fit=random.choice(FIT_CHOICES),
                        care_instructions='Machine wash cold. Do not bleach. Tumble dry low.',
                        price=price,
                        sale_price=sale_price,
                        is_new_arrival=is_new,
                        is_featured=is_featured,
                    )
                    product.collections.add(collections[random.choice(list(collections.keys()))])

                    # images: one placeholder per color used
                    chosen_colors = random.sample(list(colors.keys()), k=random.choice([2, 3]))
                    bgpalette = ['#22262b', '#3a3f47', '#5b4636', '#4a5240']
                    for idx, cname in enumerate(chosen_colors):
                        img = ProductImage(product=product, color=colors[cname],
                                            image_type='main' if idx == 0 else 'model', order=idx)
                        img.image.save(
                            f"{product.sku}-{cname}.svg",
                            ContentFile(make_placeholder_svg(f"{name}\n{cname}", bgpalette[idx % len(bgpalette)])),
                            save=False,
                        )
                        img.save()

                        for slabel in sizes:
                            stock = random.choice([0, 0, 3, 5, 8, 12, 20, 25])
                            ProductVariant.objects.get_or_create(
                                product=product, size=sizes[slabel], color=colors[cname],
                                defaults={'stock': stock},
                            )
                    products_created.append(product)

        self.stdout.write(f'Created {len(products_created)} products.')

        self.stdout.write('Seeding banners...')
        Banner.objects.get_or_create(
            placement='announcement', defaults={'message': 'FREE DELIVERY ON ORDERS ABOVE PKR 5,000'}
        )
        Banner.objects.get_or_create(
            placement='hero',
            defaults={
                'heading': "SUMMER '26 COLLECTION",
                'subheading': 'Discover the new collection',
                'cta_label': 'Shop Men',
                'cta_url': '/men',
            },
        )

        self.stdout.write('Seeding coupons...')
        now = timezone.now()
        Coupon.objects.get_or_create(
            code='SUMMER20', defaults={
                'discount_type': 'percentage', 'value': 20, 'min_order_amount': 3000,
                'start_date': now - timedelta(days=5), 'expiry_date': now + timedelta(days=60),
            },
        )
        Coupon.objects.get_or_create(
            code='WELCOME10', defaults={
                'discount_type': 'percentage', 'value': 10, 'min_order_amount': 0,
                'is_first_order_only': True,
                'start_date': now - timedelta(days=5), 'expiry_date': now + timedelta(days=365),
            },
        )

        self.stdout.write('Seeding store locations...')
        StoreLocation.objects.get_or_create(
            name='Flagship Store', city='Faisalabad', defaults={
                'address': 'D Ground, Susan Road, Faisalabad', 'phone': '041-1234567',
                'opening_hours': '11:00 AM - 10:00 PM',
            },
        )
        StoreLocation.objects.get_or_create(
            name='City Mall Outlet', city='Lahore', defaults={
                'address': 'Gulberg III, Lahore', 'phone': '042-1234567',
                'opening_hours': '11:00 AM - 10:00 PM',
            },
        )

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(username='admin', email='admin@outfitters.local', password='admin12345')
            self.stdout.write(self.style.SUCCESS('Superuser created: admin@outfitters.local / admin12345'))

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
