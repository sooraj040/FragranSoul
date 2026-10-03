"""Database models for the FraagranSoul fragrance store.

The important design choice in this file is that a Product represents the
fragrance itself, while ProductVariant represents a sellable bottle size.
This lets the admin enter different prices and stock for 8 ml, 10 ml, 20 ml,
30 ml, etc. without creating duplicate products.
"""

import secrets

from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse


class Category(models.Model):
    """A fragrance family such as Woody, Floral, Amber or Musk."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """The main perfume record shown to customers."""

    GENDER_CHOICES = [
        ("men", "Men"),
        ("women", "Women"),
        ("unisex", "Unisex"),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    brand = models.CharField(max_length=100, default="FraagranSoul")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default="unisex",
        verbose_name="For",
        help_text="Which collection the perfume is listed under.",
    )
    description = models.TextField()
    notes = models.CharField(
        max_length=250,
        blank=True,
        help_text="Example: Bergamot, amber and vanilla.",
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Perfume"
        verbose_name_plural = "Perfumes"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Return the public product-detail URL."""
        return reverse("store:product_detail", args=[self.slug])

    @property
    def available_variants(self):
        """Return only sizes that are currently in stock.

        Filtering happens in Python so pages that prefetch the variants do not
        run an extra query for every product card.
        """
        return [variant for variant in self.variants.all() if variant.stock > 0]

    @property
    def starting_price(self):
        """Show the cheapest available size price on product cards."""
        prices = [variant.price for variant in self.available_variants]
        return min(prices) if prices else None

    @property
    def on_offer(self):
        """True when at least one available size has a reduced price."""
        return any(variant.has_discount for variant in self.available_variants)

    @property
    def total_stock(self):
        """Bottles in stock across every size."""
        return sum(variant.stock for variant in self.variants.all())


class ProductVariant(models.Model):
    """A specific bottle size, price and stock level for a perfume."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    volume_ml = models.PositiveIntegerField(
        verbose_name="Bottle size (ml)",
        help_text="Enter the bottle size, e.g. 8, 10, 20 or 30.",
    )
    price = models.DecimalField(max_digits=9, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional original price shown with a strikethrough.",
    )
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["volume_ml"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "volume_ml"],
                name="unique_product_volume",
            )
        ]
        verbose_name = "Bottle Size / Variant"
        verbose_name_plural = "Bottle Sizes / Variants"

    def __str__(self):
        return f"{self.product.name} — {self.volume_ml} ml"

    @property
    def in_stock(self):
        """Convenient boolean for templates and cart validation."""
        return self.stock > 0

    @property
    def has_discount(self):
        """True when an old price is set and is higher than the current price."""
        return self.old_price is not None and self.old_price > self.price

    @property
    def discount_percent(self):
        """Whole-number saving against the old price, or 0 without a discount."""
        if not self.has_discount:
            return 0
        return int((self.old_price - self.price) * 100 / self.old_price)


def generate_order_number():
    """Return a short, hard-to-guess order reference such as FS-9F3A1C2B."""
    return f"FS-{secrets.token_hex(4).upper()}"


class Order(models.Model):
    """A placed order with the delivery details entered at checkout."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_CHOICES = [
        ("cod", "Cash on delivery"),
    ]
    # The normal path of an order, used for the progress tracker.
    STATUS_STEPS = ["pending", "confirmed", "shipped", "delivered"]

    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        default=generate_order_number,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
        help_text="Empty when the customer checked out as a guest.",
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField(verbose_name="Delivery address")
    city = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=6, verbose_name="PIN code")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cod")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def get_absolute_url(self):
        """Return the customer-facing order confirmation URL."""
        return reverse("store:order_detail", args=[self.order_number])

    @property
    def is_cancelled(self):
        return self.status == "cancelled"

    @property
    def item_count(self):
        """Total number of bottles in the order."""
        return sum(item.quantity for item in self.items.all())

    @property
    def progress(self):
        """Return (label, reached) pairs for the order progress tracker."""
        if self.is_cancelled:
            return []
        labels = dict(self.STATUS_CHOICES)
        current = self.STATUS_STEPS.index(self.status)
        return [
            (labels[step], position <= current)
            for position, step in enumerate(self.STATUS_STEPS)
        ]

    def cancel_and_restock(self):
        """Cancel the order and put its bottles back into stock.

        Returns False when the order was already cancelled, so stock is never
        returned twice.
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if order.status == "cancelled":
                return False

            for item in order.items.exclude(variant=None):
                ProductVariant.objects.filter(pk=item.variant_id).update(
                    stock=F("stock") + item.quantity
                )
            Order.objects.filter(pk=self.pk).update(status="cancelled")

        self.status = "cancelled"
        return True


class OrderItem(models.Model):
    """One purchased bottle size.

    Name, size and price are copied from the variant at checkout so the order
    stays accurate even if the perfume is later edited or deleted in Admin.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        related_name="order_items",
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=150)
    volume_ml = models.PositiveIntegerField(verbose_name="Bottle size (ml)")
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} — {self.volume_ml} ml × {self.quantity}"

    @property
    def line_total(self):
        """Price for this line (unit price × quantity)."""
        return self.unit_price * self.quantity
