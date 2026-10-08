"""Small values that should be available in every storefront template."""

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

from .models import Category


def background_music():
    """Return the music file's URL, or None when no file has been added."""
    if finders.find(settings.BACKGROUND_MUSIC_FILE):
        return static(settings.BACKGROUND_MUSIC_FILE)
    return None


def storefront(request):
    """Return the bag count, navigation families, shipping threshold and music."""
    cart = request.session.get("cart", {})
    return {
        "background_music": background_music(),
        "background_music_start": settings.BACKGROUND_MUSIC_START,
        "cart_count": sum(cart.values()),
        "nav_categories": Category.objects.filter(products__isnull=False).distinct()[:4],
        "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD,
    }
