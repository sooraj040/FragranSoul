"""Small values that should be available in every storefront template."""

from django.conf import settings

from .models import Category


def storefront(request):
    """Return the bag count, navigation families and shipping threshold."""
    cart = request.session.get("cart", {})
    return {
        "cart_count": sum(cart.values()),
        "nav_categories": Category.objects.filter(products__isnull=False).distinct()[:4],
        "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD,
    }
