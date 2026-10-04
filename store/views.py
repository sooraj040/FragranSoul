"""Views for the FragranSoul storefront.

The cart stores ProductVariant IDs rather than Product IDs because every
bottle size can have a different price and stock quantity.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F, Min, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CheckoutForm
from .models import Category, Order, OrderItem, Product, ProductVariant


class OutOfStock(Exception):
    """Raised inside the checkout transaction when stock ran out mid-order."""


def safe_next_url(request, url):
    """Return the redirect target only if it stays on this site."""
    if url and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return None


def shipping_for(subtotal):
    """Return the shipping charge for an order subtotal."""
    if subtotal >= settings.FREE_SHIPPING_THRESHOLD:
        return Decimal("0.00")
    return settings.SHIPPING_FEE


def get_cart_items(request):
    """Build the cart lines from the session and return (items, subtotal).

    Sizes that were deleted or sold out are dropped, and quantities are capped
    at the available stock. The cleaned cart is written back to the session so
    the bag, the checkout page and the placed order always agree.
    """
    cart_data = request.session.get("cart", {})
    items = []
    subtotal = Decimal("0.00")
    cleaned_cart = {}

    variants = ProductVariant.objects.select_related("product").filter(
        id__in=cart_data.keys()
    )
    variant_map = {str(variant.id): variant for variant in variants}

    for variant_id, saved_quantity in cart_data.items():
        variant = variant_map.get(str(variant_id))
        if not variant or variant.stock < 1:
            continue

        quantity = min(int(saved_quantity), variant.stock)
        if quantity < 1:
            continue

        line_subtotal = variant.price * quantity
        subtotal += line_subtotal
        cleaned_cart[str(variant_id)] = quantity

        items.append(
            {
                "variant": variant,
                "qty": quantity,
                "subtotal": line_subtotal,
            }
        )

    if cleaned_cart != cart_data:
        request.session["cart"] = cleaned_cart

    return items, subtotal


SORT_OPTIONS = {
    "new": ("Newest first", "-created_at"),
    "price_asc": ("Price: low to high", "min_price"),
    "price_desc": ("Price: high to low", "-min_price"),
    "name": ("Name: A to Z", "name"),
}


def available_products():
    """Perfumes with at least one bottle size in stock.

    `min_price` is the cheapest in-stock size, used for sorting. Variants are
    prefetched so product cards do not query the database one by one.
    """
    return (
        Product.objects.annotate(
            min_price=Min("variants__price", filter=Q(variants__stock__gt=0))
        )
        .filter(min_price__isnull=False)
        .select_related("category")
        .prefetch_related("variants")
    )


def home(request):
    """Display featured and newly added perfumes."""
    products = available_products()
    featured = products.filter(is_featured=True)[:8]
    # Until something is marked as featured, show the latest perfumes instead
    # of an empty home page.
    if not featured:
        featured = products[:8]

    return render(
        request,
        "store/home.html",
        {
            "featured": featured,
            "new_arrivals": products.filter(is_new=True)[:4],
            "collections": Product.GENDER_CHOICES,
        },
    )


def shop(request):
    """Display the collection with Men/Women/Unisex tabs, search, family filter and sorting."""
    products = available_products()

    search_query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    gender = request.GET.get("gender", "")
    if gender not in dict(Product.GENDER_CHOICES):
        gender = ""
    sort = request.GET.get("sort", "new")
    if sort not in SORT_OPTIONS:
        sort = "new"

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if gender:
        products = products.filter(gender=gender)

    products = products.order_by(SORT_OPTIONS[sort][1], "name")

    return render(
        request,
        "store/shop.html",
        {
            "products": products,
            "categories": Category.objects.all(),
            "q": search_query,
            "selected_category": category_slug,
            "gender": gender,
            "gender_label": dict(Product.GENDER_CHOICES).get(gender, ""),
            "collections": Product.GENDER_CHOICES,
            "sort": sort,
            "sort_options": [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
            "is_filtered": bool(search_query or category_slug),
        },
    )


def product_detail(request, slug):
    """Show one perfume and all of its available bottle sizes."""
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug)
    variants = list(product.variants.all())
    related = available_products().filter(category=product.category).exclude(pk=product.pk)[:4]

    return render(
        request,
        "store/product_detail.html",
        {
            "product": product,
            "variants": variants,
            # Pre-selected so the page works before the customer clicks a size.
            "default_variant": next((v for v in variants if v.in_stock), None),
            "related": related,
        },
    )


def add_to_cart(request, variant_id):
    """Add one selected bottle size to the session cart."""
    if request.method != "POST":
        return redirect("store:shop")

    variant = get_object_or_404(
        ProductVariant.objects.select_related("product"),
        pk=variant_id,
    )

    if not variant.in_stock:
        messages.error(request, "This bottle size is currently out of stock.")
        return redirect(variant.product.get_absolute_url())

    try:
        quantity = max(int(request.POST.get("quantity", 1)), 1)
    except (TypeError, ValueError):
        quantity = 1

    cart = request.session.get("cart", {})
    key = str(variant_id)
    current_quantity = int(cart.get(key, 0))

    if current_quantity >= variant.stock:
        messages.error(
            request,
            f"Only {variant.stock} of {variant.product.name} "
            f"({variant.volume_ml} ml) available, and they are already in your bag.",
        )
    else:
        cart[key] = min(current_quantity + quantity, variant.stock)
        request.session["cart"] = cart
        messages.success(
            request,
            f"{variant.product.name} ({variant.volume_ml} ml) added to your bag.",
        )

    next_url = safe_next_url(request, request.POST.get("next"))
    return redirect(next_url or variant.product.get_absolute_url())


def cart(request):
    """Build the shopping bag from the selected bottle-size variants."""
    items, subtotal = get_cart_items(request)
    shipping = shipping_for(subtotal)
    return render(
        request,
        "store/cart.html",
        {
            "items": items,
            "subtotal": subtotal,
            "shipping": shipping,
            "total": subtotal + shipping,
        },
    )


@require_POST
def update_cart(request, variant_id):
    """Change the quantity of one bottle-size variant in the cart."""
    cart_data = request.session.get("cart", {})
    key = str(variant_id)
    variant = get_object_or_404(ProductVariant, pk=variant_id)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    quantity = min(quantity, variant.stock)
    if quantity <= 0:
        cart_data.pop(key, None)
    else:
        cart_data[key] = quantity

    request.session["cart"] = cart_data
    return redirect("store:cart")


@require_POST
def remove_from_cart(request, variant_id):
    """Remove one bottle-size variant from the cart."""
    cart_data = request.session.get("cart", {})
    cart_data.pop(str(variant_id), None)
    request.session["cart"] = cart_data
    return redirect("store:cart")


def place_order(request, form):
    """Save the order, reduce stock and return the new Order.

    Everything happens in one database transaction. Stock is only reduced when
    enough is still available, so two customers can never buy the same last
    bottle; if that happens OutOfStock is raised and nothing is saved.
    """
    cart_data = request.session.get("cart", {})

    with transaction.atomic():
        variants = (
            ProductVariant.objects.select_for_update()
            .select_related("product")
            .filter(id__in=cart_data.keys())
        )
        variant_map = {str(variant.id): variant for variant in variants}

        lines = []
        subtotal = Decimal("0.00")
        for variant_id, saved_quantity in cart_data.items():
            variant = variant_map.get(str(variant_id))
            quantity = int(saved_quantity)
            if not variant or quantity < 1 or variant.stock < quantity:
                raise OutOfStock
            lines.append((variant, quantity))
            subtotal += variant.price * quantity

        if not lines:
            raise OutOfStock

        shipping = shipping_for(subtotal)
        order = form.save(commit=False)
        order.user = request.user if request.user.is_authenticated else None
        order.subtotal = subtotal
        order.shipping = shipping
        order.total = subtotal + shipping
        order.save()

        for variant, quantity in lines:
            updated = ProductVariant.objects.filter(
                pk=variant.pk,
                stock__gte=quantity,
            ).update(stock=F("stock") - quantity)
            if not updated:
                raise OutOfStock

            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                volume_ml=variant.volume_ml,
                unit_price=variant.price,
                quantity=quantity,
            )

    return order


def checkout(request):
    """Collect delivery details and place the order."""
    items, subtotal = get_cart_items(request)
    if not items:
        return redirect("store:shop")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request, form)
            except OutOfStock:
                messages.error(
                    request,
                    "Some items in your bag are no longer available in that "
                    "quantity. Please review your bag and try again.",
                )
                return redirect("store:cart")

            request.session["cart"] = {}
            # Lets guests open the confirmation page for orders they placed.
            request.session["orders"] = request.session.get("orders", []) + [order.order_number]
            return redirect(order.get_absolute_url())
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "full_name": request.user.get_full_name(),
                "email": request.user.email,
            }
        form = CheckoutForm(initial=initial)

    shipping = shipping_for(subtotal)
    return render(
        request,
        "store/checkout.html",
        {
            "form": form,
            "items": items,
            "subtotal": subtotal,
            "shipping": shipping,
            "total": subtotal + shipping,
        },
    )


def order_detail(request, order_number):
    """Show the confirmation for one order to the customer who placed it."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_number=order_number,
    )

    is_owner = request.user.is_authenticated and order.user_id == request.user.id
    placed_in_this_session = order.order_number in request.session.get("orders", [])
    if not (is_owner or placed_in_this_session or request.user.is_staff):
        raise Http404

    return render(request, "store/order_success.html", {"order": order})


@login_required
def order_history(request):
    """List every order placed by the signed-in customer."""
    orders = request.user.orders.prefetch_related("items")
    return render(request, "accounts/orders.html", {"orders": orders})


def account_login(request):
    """Authenticate a customer using their email as the Django username."""
    if request.method == "POST":
        identifier = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        # Customers sign in with their email (stored in lower case); staff
        # accounts created from the command line may use a plain username.
        user = authenticate(request, username=identifier.lower(), password=password) or authenticate(
            request, username=identifier, password=password
        )

        if user:
            login(request, user)
            next_url = safe_next_url(request, request.GET.get("next"))
            # Staff land on the dashboard; customers go back to the store.
            return redirect(next_url or ("store:dashboard" if user.is_staff else "store:home"))

        messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login.html", {"next": request.GET.get("next", "")})


def account_register(request):
    """Create a basic customer account."""
    values = {}

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        values = {"first_name": first_name, "last_name": last_name, "email": email}

        user = User(username=email, email=email, first_name=first_name, last_name=last_name)
        try:
            validate_email(email)
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")
            if User.objects.filter(username=email).exists():
                raise ValidationError("An account with this email already exists.")
            validate_password(password, user=user)
        except ValidationError as error:
            for error_message in error.messages:
                messages.error(request, error_message)
        else:
            user.set_password(password)
            user.save()
            login(request, user)
            return redirect("store:home")

    return render(request, "accounts/register.html", {"values": values})


@require_POST
def account_logout(request):
    """Log out the current customer and return to the home page."""
    logout(request)
    return redirect("store:home")
