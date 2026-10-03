"""Load perfumes and their bottle sizes from a CSV file.

Usage:
    python manage.py import_products products.csv
    python manage.py import_products products.csv --dry-run

The CSV has one row per bottle size. Rows that share the same perfume name
become one perfume with several sizes. Running the import again updates the
existing perfumes instead of creating duplicates.
"""

import csv
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from store.models import Category, Product, ProductVariant

REQUIRED_COLUMNS = {"name", "category", "volume_ml", "price"}
TRUE_VALUES = {"1", "true", "yes", "y"}


class Command(BaseCommand):
    help = "Import perfumes and bottle sizes from a CSV file (one row per bottle size)."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the CSV file.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Check the file and report what would change without saving.",
        )

    def handle(self, *args, **options):
        try:
            # utf-8-sig also accepts files saved from Excel, which add a BOM.
            with open(options["csv_file"], newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
        except OSError as error:
            raise CommandError(f"Cannot read {options['csv_file']}: {error}")

        if not rows:
            raise CommandError("The CSV file has no product rows.")

        missing = REQUIRED_COLUMNS - set(rows[0].keys())
        if missing:
            raise CommandError(f"Missing required column(s): {', '.join(sorted(missing))}")

        products_seen = set()
        with transaction.atomic():
            # Row 1 is the header, so product rows start at line 2.
            for line_number, row in enumerate(rows, start=2):
                try:
                    product = self.import_row(row)
                except ValueError as error:
                    raise CommandError(f"Line {line_number}: {error}")
                products_seen.add(product.pk)

            if options["dry_run"]:
                transaction.set_rollback(True)

        summary = f"{len(products_seen)} perfume(s), {len(rows)} bottle size(s)"
        if options["dry_run"]:
            self.stdout.write(f"Dry run OK: {summary} would be imported. Nothing was saved.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Imported {summary}."))

    def import_row(self, row):
        """Create or update the perfume and bottle size described by one row."""
        row = {key: (value or "").strip() for key, value in row.items() if key}

        name = row["name"]
        category_name = row["category"]
        if not name or not category_name:
            raise ValueError("name and category are required.")

        category = Category.objects.filter(name__iexact=category_name).first()
        if category is None:
            category = Category.objects.create(name=category_name, slug=slugify(category_name))

        product_fields = {"name": name, "category": category}
        for column in ("brand", "description", "notes"):
            if row.get(column):
                product_fields[column] = row[column]
        if row.get("gender"):
            gender = row["gender"].lower()
            if gender not in dict(Product.GENDER_CHOICES):
                raise ValueError("gender must be men, women or unisex.")
            product_fields["gender"] = gender
        for column in ("is_featured", "is_new"):
            if row.get(column):
                product_fields[column] = row[column].lower() in TRUE_VALUES
        if row.get("image"):
            image_path = f"products/{row['image']}"
            if not (settings.MEDIA_ROOT / image_path).is_file():
                raise ValueError(f"image '{row['image']}' was not found in media/products/.")
            product_fields["image"] = image_path

        product, _ = Product.objects.update_or_create(
            slug=slugify(name),
            defaults=product_fields,
        )

        try:
            volume_ml = int(row["volume_ml"])
            price = Decimal(row["price"])
            old_price = Decimal(row["old_price"]) if row.get("old_price") else None
            stock = int(row["stock"]) if row.get("stock") else 0
        except (ValueError, InvalidOperation):
            raise ValueError("volume_ml, price, old_price and stock must be numbers.")
        if volume_ml <= 0 or price <= 0 or stock < 0:
            raise ValueError("volume_ml and price must be above zero; stock cannot be negative.")

        ProductVariant.objects.update_or_create(
            product=product,
            volume_ml=volume_ml,
            defaults={"price": price, "old_price": old_price, "stock": stock},
        )
        return product
