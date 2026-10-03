"""Staff dashboard for running the store: orders, perfumes and families.

Every view here is restricted to staff accounts. The built-in Django admin at
/admin/ remains available; this dashboard covers the day-to-day tasks with the
store's own look and feel.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CategoryForm, ProductForm, VariantFormSet
from .models import Category, Order, Product, ProductVariant

LOW_STOCK_LEVEL = 3


def staff_required(view):
    """Send visitors to sign in, and refuse signed-in customers."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


@staff_required
def overview(request):
    """Headline numbers, recent orders and sizes that are running low."""
    active_orders = Order.objects.exclude(status="cancelled")
    today = timezone.localdate()

    return render(
        request,
        "dashboard/overview.html",
        {
            "section": "overview",
            "orders_total": Order.objects.count(),
            "orders_today": Order.objects.filter(created_at__date=today).count(),
            "orders_pending": Order.objects.filter(status="pending").count(),
            "order_value": active_orders.aggregate(value=Sum("total"))["value"] or 0,
            "perfume_count": Product.objects.count(),
            "recent_orders": Order.objects.prefetch_related("items")[:6],
            "low_stock": ProductVariant.objects.select_related("product")
            .filter(stock__lte=LOW_STOCK_LEVEL)
            .order_by("stock", "product__name")[:8],
            "low_stock_level": LOW_STOCK_LEVEL,
        },
    )


@staff_required
def orders(request):
    """Every order, newest first, with status filter and search."""
    order_list = Order.objects.prefetch_related("items")

    status = request.GET.get("status", "")
    search_query = request.GET.get("q", "").strip()

    if status in dict(Order.STATUS_CHOICES):
        order_list = order_list.filter(status=status)
    else:
        status = ""

    if search_query:
        order_list = order_list.filter(
            Q(order_number__icontains=search_query)
            | Q(full_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

    page = Paginator(order_list, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/orders.html",
        {
            "section": "orders",
            "page": page,
            "status": status,
            "q": search_query,
            "status_choices": Order.STATUS_CHOICES,
        },
    )


@staff_required
def order(request, order_number):
    """One order: customer details, items and status changes."""
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_number=order_number)

    if request.method == "POST":
        action = request.POST.get("action")
        new_status = request.POST.get("status")

        if order.is_cancelled:
            messages.error(request, "A cancelled order cannot be changed.")
        elif action == "cancel":
            order.cancel_and_restock()
            messages.success(request, f"Order {order.order_number} cancelled and items returned to stock.")
        elif action == "status" and new_status in Order.STATUS_STEPS:
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"Order marked as {order.get_status_display().lower()}.")

        return redirect("store:dashboard_order", order_number=order.order_number)

    return render(
        request,
        "dashboard/order_detail.html",
        {
            "section": "orders",
            "order": order,
            "status_steps": [(value, label) for value, label in Order.STATUS_CHOICES if value != "cancelled"],
        },
    )


@staff_required
def products(request):
    """Every perfume, including ones that are sold out."""
    product_list = Product.objects.select_related("category").prefetch_related("variants")

    search_query = request.GET.get("q", "").strip()
    if search_query:
        product_list = product_list.filter(
            Q(name__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    return render(
        request,
        "dashboard/products.html",
        {"section": "products", "products": product_list, "q": search_query},
    )


@staff_required
def product_edit(request, pk=None):
    """Add a perfume, or edit one together with its bottle sizes."""
    product = get_object_or_404(Product, pk=pk) if pk else Product()

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = VariantFormSet(request.POST, instance=product)
        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()
            messages.success(request, f"{product.name} saved.")
            return redirect("store:dashboard_products")
    else:
        form = ProductForm(instance=product)
        formset = VariantFormSet(instance=product)

    return render(
        request,
        "dashboard/product_form.html",
        {
            "section": "products",
            "form": form,
            "formset": formset,
            "product": product if pk else None,
            "has_categories": Category.objects.exists(),
        },
    )


@staff_required
@require_POST
def product_delete(request, pk):
    """Delete a perfume. Past orders keep their own copy of name and price."""
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f"{name} deleted.")
    return redirect("store:dashboard_products")


@staff_required
def categories(request):
    """List fragrance families and add new ones."""
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"{category.name} added.")
        return redirect("store:dashboard_categories")

    return render(
        request,
        "dashboard/categories.html",
        {
            "section": "categories",
            "form": form,
            "categories": Category.objects.annotate(product_count=Count("products")),
        },
    )


@staff_required
@require_POST
def category_delete(request, pk):
    """Delete an empty family. Families that still hold perfumes are kept."""
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.error(
            request,
            f"{category.name} still has perfumes. Move or delete them first.",
        )
    else:
        category.delete()
        messages.success(request, f"{category.name} deleted.")
    return redirect("store:dashboard_categories")
