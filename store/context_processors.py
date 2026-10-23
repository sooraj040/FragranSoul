"""Small values that should be available in every storefront template."""

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static


def background_music():
    """Return the music file's URL, or None when no file has been added."""
    if finders.find(settings.BACKGROUND_MUSIC_FILE):
        return static(settings.BACKGROUND_MUSIC_FILE)
    return None


def storefront(request):
    """Return the bag count, shipping threshold and music."""
    cart = request.session.get("cart", {})
    return {
        "background_music": background_music(),
        "background_music_start": settings.BACKGROUND_MUSIC_START,
        "cart_count": sum(cart.values()),
        "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD,
    }
