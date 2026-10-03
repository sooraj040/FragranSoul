"""Django admin configuration for client-friendly product management."""

from django.contrib import admin, messages

from .models import Category, Order, OrderItem, Product, ProductVariant


class ProductVariantInline(admin.TabularInline):
    """Lets the client manage every bottle size from the perfume page."""

    model = ProductVariant
    extra = 1
    min_num = 1
    fields = ("volume_ml", "price", "old_price", "stock")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin settings for fragrance families."""

    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Main perfume admin page, including all bottle-size variants."""

    list_display = (
        "name",
        "brand",
        "category",
        "gender",
        "starting_price_display",
        "is_featured",
        "is_new",
    )
    list_filter = ("gender", "category", "is_featured", "is_new")
    search_fields = ("name", "brand", "notes")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at",)
    inlines = [ProductVariantInline]

    @admin.display(description="Starting price")
    def starting_price_display(self, obj):
        """Show the cheapest in-stock bottle size in the product list."""
        return obj.starting_price or "—"


class OrderItemInline(admin.TabularInline):
    """Read-only list of what the customer bought."""

    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "volume_ml", "unit_price", "quantity", "line_total")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Orders placed on the storefront. Change the status as the order progresses."""

    list_display = ("order_number", "full_name", "phone", "city", "total", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("order_number", "full_name", "email", "phone")
    date_hierarchy = "created_at"
    readonly_fields = (
        "order_number",
        "user",
        "payment_method",
        "subtotal",
        "shipping",
        "total",
        "created_at",
    )
    inlines = [OrderItemInline]
    actions = ["cancel_and_restock"]

    def has_add_permission(self, request):
        """Orders are only created by customers at checkout."""
        return False

    @admin.action(description="Cancel selected orders and return items to stock")
    def cancel_and_restock(self, request, queryset):
        """Cancel orders and put their bottles back into stock."""
        cancelled = sum(order.cancel_and_restock() for order in queryset)

        self.message_user(request, f"{cancelled} order(s) cancelled and restocked.", messages.SUCCESS)
