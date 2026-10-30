"""
Drop real product photos into media/product_photos_incoming/ and this
command wires them up to the right Product + Color automatically,
replacing the seeded placeholder SVGs.

FILENAME CONVENTION (case-insensitive, spaces/underscores treated as dashes):

    <SKU>-<ColorName>.<ext>          -> replaces that color's MAIN image
    <SKU>-<ColorName>-2.<ext>        -> added as an extra image (front/back/model...)
    <SKU>-<ColorName>-3.<ext>        -> etc.

    Examples:
        OF-1016-Navy.jpg
        OF-1016-Navy-2.jpg
        OF-1016-Navy-3.jpg
        OF-1007-Olive.png

Accepted extensions: jpg, jpeg, png, webp

USAGE:
    # See exactly which SKU-Color filenames every product currently expects
    python manage.py import_product_photos --list

    # Import everything sitting in the default incoming folder
    python manage.py import_product_photos

    # Import from a custom folder
    python manage.py import_product_photos --source /path/to/photos
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import Product, Color, ProductImage

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# main / model / front / back / closeup, in the order extra shots should be tagged
EXTRA_IMAGE_TYPE_CYCLE = ['model', 'front', 'back', 'closeup']

FILENAME_RE = re.compile(
    r'^(?P<sku>[A-Za-z]+-\d+)[-_ ]+(?P<color>[A-Za-z]+)(?:[-_ ]+(?P<seq>\d+))?$'
)


class Command(BaseCommand):
    help = 'Match dropped photo files (SKU-Color.ext) to Products/Colors and attach them.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', default=None,
            help='Folder to read photos from (default: media/product_photos_incoming/)',
        )
        parser.add_argument(
            '--list', action='store_true',
            help='Just print the SKU-Color filenames every product expects, then exit.',
        )
        parser.add_argument(
            '--keep', action='store_true',
            help='Keep source files in place instead of deleting them after a successful import.',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.print_expected_filenames()
            return

        source_dir = Path(options['source']) if options['source'] else (
            Path(settings.MEDIA_ROOT) / 'product_photos_incoming'
        )
        source_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(
            p for p in source_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
        )
        if not files:
            self.stdout.write(self.style.WARNING(
                f'No image files found in {source_dir}. '
                f'Drop files named like OF-1016-Navy.jpg there and re-run.'
            ))
            self.stdout.write('Run with --list to see exactly which SKU-Color names are expected.')
            return

        matched, unmatched, errors = 0, [], []

        for path in files:
            stem = path.stem  # filename without extension
            m = FILENAME_RE.match(stem)
            if not m:
                unmatched.append((path.name, 'filename does not match SKU-Color[-N] pattern'))
                continue

            sku = m.group('sku').upper()
            color_name = m.group('color')
            seq = int(m.group('seq')) if m.group('seq') else 1

            try:
                product = Product.objects.get(sku__iexact=sku)
            except Product.DoesNotExist:
                unmatched.append((path.name, f'no product with SKU {sku}'))
                continue

            try:
                color = Color.objects.get(name__iexact=color_name)
            except Color.DoesNotExist:
                unmatched.append((path.name, f'no color named "{color_name}"'))
                continue

            data = path.read_bytes()
            new_name = f"{sku}-{color.name}{'' if seq == 1 else f'-{seq}'}{path.suffix.lower()}"

            if seq == 1:
                # Replace (or create) the MAIN image for this product+color
                img, created = ProductImage.objects.get_or_create(
                    product=product, color=color, image_type='main',
                    defaults={'order': 0},
                )
                # remove the old file (placeholder or previous photo) before saving the new one
                if img.image and not created:
                    img.image.delete(save=False)
                img.image.save(new_name, ContentFile(data), save=True)
                matched += 1
            else:
                image_type = EXTRA_IMAGE_TYPE_CYCLE[(seq - 2) % len(EXTRA_IMAGE_TYPE_CYCLE)]
                img = ProductImage(product=product, color=color, image_type=image_type, order=seq - 1)
                img.image.save(new_name, ContentFile(data), save=True)
                matched += 1

            if not options['keep']:
                path.unlink()

        self.stdout.write(self.style.SUCCESS(f'Attached {matched} photo(s).'))
        if unmatched:
            self.stdout.write(self.style.WARNING(f'{len(unmatched)} file(s) skipped:'))
            for name, reason in unmatched:
                self.stdout.write(f'  - {name}: {reason}')
            for name, reason in errors:
                self.stdout.write(f'  - {name}: {reason}')

    def print_expected_filenames(self):
        products = Product.objects.prefetch_related('images__color').order_by('sku')
        if not products.exists():
            self.stdout.write(self.style.WARNING(
                'No products in the database yet — run "python manage.py seed_data" first, '
                'then re-run this with --list.'
            ))
            return

        self.stdout.write('sku,color,product_name,expected_filename')
        for product in products:
            colors_seen = set()
            for img in product.images.all():
                if img.color_id and img.color_id not in colors_seen:
                    colors_seen.add(img.color_id)
                    self.stdout.write(
                        f'{product.sku},{img.color.name},{product.name},'
                        f'{product.sku}-{img.color.name}.jpg'
                    )
