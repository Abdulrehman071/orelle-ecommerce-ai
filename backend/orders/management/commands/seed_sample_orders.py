"""
Create realistic DEMO orders so the AI Business Assistant has sales data to analyse.

    python manage.py seed_sample_orders                 # 150 orders spread over the last 90 days
    python manage.py seed_sample_orders --orders 300 --days 120
    python manage.py seed_sample_orders --clear         # remove ALL demo orders and put their stock back

Every demo order has an order number starting with "DMO-" and a customer email ending in
@example.com, so they can always be told apart from real orders and removed cleanly.
Stock is reduced for non-cancelled demo orders (like a real checkout) and restored by --clear.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalog.models import ProductVariant
from orders.models import Order, OrderItem, Shipment

PREFIX = 'DMO-'
FREE_SHIPPING_THRESHOLD = Decimal('5000')   # same rules as orders/views.py
STANDARD_FEE, EXPRESS_FEE = Decimal('250'), Decimal('600')
CITIES = [('Lahore', 'Punjab'), ('Karachi', 'Sindh'), ('Islamabad', 'Islamabad Capital Territory'),
          ('Multan', 'Punjab'), ('Faisalabad', 'Punjab'), ('Rawalpindi', 'Punjab'), ('Peshawar', 'Khyber Pakhtunkhwa')]
FIRST = ['Ayesha', 'Bilal', 'Hira', 'Usman', 'Fatima', 'Hamza', 'Sana', 'Ali', 'Zainab', 'Omar', 'Maryam', 'Hassan']
LAST = ['Khan', 'Ahmed', 'Malik', 'Raza', 'Sheikh', 'Butt', 'Iqbal', 'Chaudhry', 'Siddiqui', 'Hussain']
CARRIERS = ['TCS', 'Leopards', 'M&P']


class Command(BaseCommand):
    help = 'Create (or --clear) demo orders for testing the AI business assistant.'

    def add_arguments(self, parser):
        parser.add_argument('--orders', type=int, default=150)
        parser.add_argument('--days', type=int, default=90, help='Spread orders over this many past days')
        parser.add_argument('--seed', type=int, default=42, help='Random seed (same seed = same data)')
        parser.add_argument('--clear', action='store_true', help='Delete demo orders and restore their stock')

    def handle(self, *args, **o):
        if o['clear']:
            return self.clear()
        if Order.objects.filter(order_number__startswith=PREFIX).exists():
            raise CommandError('Demo orders already exist. Run with --clear first if you want to regenerate them.')
        if o['orders'] < 1 or o['days'] < 1:
            raise CommandError('--orders and --days must be positive')

        rng = random.Random(o['seed'])
        variants = list(ProductVariant.objects.select_related('product', 'size', 'color')
                        .filter(product__is_active=True, stock__gt=0))
        if not variants:
            raise CommandError('No products with stock found. Run "python manage.py seed_data" first.')
        by_product = {}
        for v in variants:
            by_product.setdefault(v.product_id, []).append(v)
        pids = list(by_product)
        rng.shuffle(pids)
        weights = [1 / (rank + 1) ** 0.9 for rank in range(len(pids))]      # a few best sellers, a long tail
        stock = {v.id: v.stock for v in variants}
        now = timezone.now()
        made = 0

        with transaction.atomic():
            for i in range(o['orders']):
                created = now - timedelta(days=int(o['days'] * rng.random() ** 1.4), hours=rng.randint(0, 23),
                                          minutes=rng.randint(0, 59))
                age_days = (now - created).days
                picked, lines = set(), []
                for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
                    pid = rng.choices(pids, weights)[0]
                    avail = [v for v in by_product[pid] if stock[v.id] > 0 and v.id not in picked]
                    if not avail:
                        continue
                    v = rng.choice(avail)
                    qty = min(rng.choices([1, 2, 3], [80, 15, 5])[0], stock[v.id])
                    picked.add(v.id)
                    lines.append((v, qty))
                if not lines:
                    continue
                status = self._status(rng, age_days)
                subtotal = sum((v.product.current_price * q for v, q in lines), Decimal(0))
                express = rng.random() < 0.2
                shipping = Decimal(0) if subtotal >= FREE_SHIPPING_THRESHOLD else (EXPRESS_FEE if express else STANDARD_FEE)
                coupon = 'WELCOME10' if rng.random() < 0.12 else ''
                discount = (subtotal * Decimal('0.10')).quantize(Decimal('1')) if coupon else Decimal(0)
                city, province = rng.choice(CITIES)
                n = rng.randint(1, 60)
                order = Order.objects.create(
                    order_number=f'{PREFIX}{10001 + i}', email=f'demo.customer{n}@example.com',
                    phone='03' + ''.join(rng.choices('0123456789', k=9)),
                    shipping_full_name=f'{rng.choice(FIRST)} {rng.choice(LAST)}', shipping_address=f'House {rng.randint(1, 300)}, Demo Street',
                    shipping_city=city, shipping_province=province,
                    delivery_method='express' if express else 'standard',
                    payment_method=rng.choices(['cod', 'bank_transfer', 'card'], [70, 15, 15])[0],
                    subtotal=subtotal, shipping_fee=shipping, discount_amount=discount,
                    total=subtotal + shipping - discount, coupon_code=coupon, status=status)
                Order.objects.filter(pk=order.pk).update(created_at=created, updated_at=created)  # auto_now_add override
                for v, q in lines:
                    OrderItem.objects.create(order=order, variant=v, product_name=v.product.name, size_label=v.size.label,
                                             color_name=v.color.name, unit_price=v.product.current_price, quantity=q)
                    if status != 'cancelled':
                        stock[v.id] -= q
                        ProductVariant.objects.filter(pk=v.pk).update(stock=stock[v.id])
                if status in ('shipped', 'out_for_delivery', 'delivered'):
                    Shipment.objects.create(
                        order=order, carrier=rng.choice(CARRIERS), tracking_number=f'DMO{rng.randint(10**8, 10**9 - 1)}',
                        shipped_at=created + timedelta(days=1),
                        delivered_at=created + timedelta(days=rng.randint(3, 6)) if status == 'delivered' else None,
                        estimated_delivery_days='2-4' if express else '5-7')
                made += 1
        self.stdout.write(self.style.SUCCESS(f'Created {made} demo orders (numbers {PREFIX}xxxxx) over the last {o["days"]} days.'))
        self.stdout.write('Remove them any time with:  python manage.py seed_sample_orders --clear')

    @staticmethod
    def _status(rng, age_days):
        if age_days <= 2:
            return rng.choices(['placed', 'confirmed', 'processing', 'cancelled'], [40, 30, 25, 5])[0]
        if age_days <= 14:
            return rng.choices(['processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled'], [10, 25, 10, 47, 8])[0]
        return rng.choices(['delivered', 'cancelled', 'shipped'], [88, 9, 3])[0]

    def clear(self):
        qs = Order.objects.filter(order_number__startswith=PREFIX)
        n = qs.count()
        with transaction.atomic():
            for item in OrderItem.objects.filter(order__in=qs).exclude(order__status='cancelled'):
                # F() adds inside the database, so several orders for the same variant all get restored
                ProductVariant.objects.filter(pk=item.variant_id).update(stock=F('stock') + item.quantity)
            qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Removed {n} demo orders and restored their stock.'))
