"""End-to-end tests for the storefront: browsing, bag, checkout and accounts."""

import tempfile
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .forms import CheckoutForm
from .models import Category, Order, Product, ProductVariant
from .views import OutOfStock, place_order

DELIVERY = {
    "full_name": "Test Customer",
    "email": "customer@example.com",
    "phone": "9876543210",
    "address": "12 Test Street",
    "city": "Kochi",
    "pin_code": "682001",
}


class StoreTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Woody", slug="woody")
        cls.product = Product.objects.create(
            name="Test Oud",
            slug="test-oud",
            category=cls.category,
            description="A test perfume.",
            notes="Oud, amber",
            is_featured=True,
        )
        cls.small = ProductVariant.objects.create(
            product=cls.product, volume_ml=10, price=Decimal("500"), stock=3
        )
        cls.large = ProductVariant.objects.create(
            product=cls.product, volume_ml=30, price=Decimal("1200"), old_price=Decimal("1500"), stock=0
        )

    def add(self, variant):
        return self.client.post(reverse("store:add_to_cart", args=[variant.id]))


class BrowsingTests(StoreTestCase):
    def test_pages_render(self):
        for url in (
            reverse("store:home"),
            reverse("store:shop"),
            self.product.get_absolute_url(),
            reverse("store:cart"),
            reverse("store:login"),
            reverse("store:register"),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_product_card_shows_cheapest_in_stock_price(self):
        self.assertContains(self.client.get(reverse("store:shop")), "From ₹500")

    def test_search_and_category_filter(self):
        shop = reverse("store:shop")
        self.assertContains(self.client.get(shop, {"q": "amber"}), "Test Oud")
        self.assertNotContains(self.client.get(shop, {"q": "citrus"}), "Test Oud")
        self.assertContains(self.client.get(shop, {"category": "woody"}), "Test Oud")
        self.assertNotContains(self.client.get(shop, {"category": "floral"}), "Test Oud")

    def test_product_page_sizes(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, f'data-variant-id="{self.small.id}"')
        self.assertContains(response, "Out of stock")
        self.assertContains(response, 'data-old-price="1500.00"')
        # The add-to-bag script must not look up elements missing from the page.
        self.assertNotContains(response, 'getElementById("variant-id")')


class CartTests(StoreTestCase):
    def test_add_caps_at_stock(self):
        for _ in range(5):
            self.add(self.small)
        self.assertEqual(self.client.session["cart"], {str(self.small.id): 3})

    def test_cannot_add_sold_out_size(self):
        self.add(self.large)
        self.assertNotIn("cart", self.client.session)

    def test_update_and_remove(self):
        self.add(self.small)
        update = reverse("store:update_cart", args=[self.small.id])
        self.client.post(update, {"quantity": 99})
        self.assertEqual(self.client.session["cart"], {str(self.small.id): 3})
        self.client.post(update, {"quantity": 0})
        self.assertEqual(self.client.session["cart"], {})

        self.add(self.small)
        remove = reverse("store:remove_from_cart", args=[self.small.id])
        self.assertEqual(self.client.get(remove).status_code, 405)
        self.client.post(remove)
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_totals(self):
        self.add(self.small)
        self.add(self.small)
        response = self.client.get(reverse("store:cart"))
        self.assertEqual(response.context["total"], Decimal("1000"))

    def test_external_next_redirect_is_ignored(self):
        response = self.client.post(
            reverse("store:add_to_cart", args=[self.small.id]),
            {"next": "https://evil.example/"},
        )
        self.assertRedirects(response, self.product.get_absolute_url())


class CheckoutTests(StoreTestCase):
    def test_empty_cart_redirects_to_shop(self):
        self.assertRedirects(self.client.get(reverse("store:checkout")), reverse("store:shop"))

    def test_guest_order_is_saved_and_stock_reduced(self):
        self.add(self.small)
        self.add(self.small)
        response = self.client.post(reverse("store:checkout"), DELIVERY)

        order = Order.objects.get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertIsNone(order.user)
        self.assertEqual(order.total, Decimal("1000"))
        self.assertEqual(order.status, "pending")
        item = order.items.get()
        self.assertEqual((item.product_name, item.volume_ml, item.quantity), ("Test Oud", 10, 2))
        self.assertEqual(item.unit_price, Decimal("500"))

        self.small.refresh_from_db()
        self.assertEqual(self.small.stock, 1)
        self.assertEqual(self.client.session["cart"], {})
        self.assertContains(self.client.get(order.get_absolute_url()), order.order_number)

    def test_invalid_details_do_not_place_order(self):
        self.add(self.small)
        bad = dict(DELIVERY, phone="12345", pin_code="12")
        response = self.client.post(reverse("store:checkout"), bad)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid 10-digit mobile number.")
        self.assertContains(response, "Enter a valid 6-digit PIN code.")
        self.assertEqual(Order.objects.count(), 0)
        self.small.refresh_from_db()
        self.assertEqual(self.small.stock, 3)

    def test_bag_is_capped_when_stock_drops(self):
        self.add(self.small)
        self.add(self.small)
        # Another customer buys two of the three bottles first.
        ProductVariant.objects.filter(pk=self.small.pk).update(stock=1)

        self.client.post(reverse("store:checkout"), DELIVERY)
        order = Order.objects.get()
        self.assertEqual(order.items.get().quantity, 1)
        self.small.refresh_from_db()
        self.assertEqual(self.small.stock, 0)

    def test_sold_out_bag_cannot_be_ordered(self):
        self.add(self.small)
        ProductVariant.objects.filter(pk=self.small.pk).update(stock=0)
        response = self.client.post(reverse("store:checkout"), DELIVERY)
        self.assertRedirects(response, reverse("store:shop"))
        self.assertEqual(Order.objects.count(), 0)

    def test_place_order_never_oversells(self):
        request = RequestFactory().post("/checkout/")
        request.session = {"cart": {str(self.small.id): 5}}
        request.user = User(username="x")
        form = CheckoutForm(DELIVERY)
        self.assertTrue(form.is_valid())
        with self.assertRaises(OutOfStock):
            place_order(request, form)
        self.assertEqual(Order.objects.count(), 0)
        self.small.refresh_from_db()
        self.assertEqual(self.small.stock, 3)

    @override_settings(SHIPPING_FEE=Decimal("80"), FREE_SHIPPING_THRESHOLD=Decimal("2000"))
    def test_shipping_fee_applies_below_threshold(self):
        self.add(self.small)
        self.client.post(reverse("store:checkout"), DELIVERY)
        order = Order.objects.get()
        self.assertEqual(
            (order.subtotal, order.shipping, order.total),
            (Decimal("500"), Decimal("80"), Decimal("580")),
        )

    def test_other_visitors_cannot_view_order(self):
        self.add(self.small)
        self.client.post(reverse("store:checkout"), DELIVERY)
        order = Order.objects.get()
        self.client.cookies.clear()
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 404)


class AccountTests(StoreTestCase):
    REGISTRATION = {
        "first_name": "Asha",
        "last_name": "Nair",
        "email": "Asha@Example.com",
        "password": "scent-of-rain-42",
        "confirm_password": "scent-of-rain-42",
    }

    def test_register_login_logout(self):
        self.assertRedirects(self.client.post(reverse("store:register"), self.REGISTRATION), reverse("store:home"))
        self.assertTrue(User.objects.filter(username="asha@example.com").exists())

        self.assertEqual(self.client.get(reverse("store:logout")).status_code, 405)
        self.client.post(reverse("store:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

        self.client.post(reverse("store:login"), {"email": "ASHA@example.com", "password": "scent-of-rain-42"})
        self.assertIn("_auth_user_id", self.client.session)

    def test_weak_or_mismatched_password_rejected(self):
        weak = dict(self.REGISTRATION, password="12345", confirm_password="12345")
        self.client.post(reverse("store:register"), weak)
        mismatch = dict(self.REGISTRATION, confirm_password="something-else-9")
        self.client.post(reverse("store:register"), mismatch)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_rejected(self):
        self.client.post(reverse("store:register"), self.REGISTRATION)
        self.client.post(reverse("store:logout"))
        self.client.post(reverse("store:register"), self.REGISTRATION)
        self.assertEqual(User.objects.count(), 1)

    def test_order_history_lists_only_own_orders(self):
        history = reverse("store:order_history")
        self.assertRedirects(self.client.get(history), f"{reverse('store:login')}?next={history}")

        self.client.post(reverse("store:register"), self.REGISTRATION)
        self.add(self.small)
        self.client.post(reverse("store:checkout"), DELIVERY)
        order = Order.objects.get()
        self.assertEqual(order.user.username, "asha@example.com")
        self.assertContains(self.client.get(history), order.order_number)

        self.client.post(reverse("store:logout"))
        other = dict(self.REGISTRATION, email="other@example.com")
        self.client.post(reverse("store:register"), other)
        self.assertNotContains(self.client.get(history), order.order_number)
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 404)


class AdminTests(StoreTestCase):
    def test_cancel_and_restock_action(self):
        self.add(self.small)
        self.client.post(reverse("store:checkout"), DELIVERY)
        order = Order.objects.get()

        User.objects.create_superuser("owner", password="owner-pass-123")
        self.client.login(username="owner", password="owner-pass-123")
        changelist = reverse("admin:store_order_changelist")
        self.assertEqual(self.client.get(changelist).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:store_order_change", args=[order.pk])).status_code, 200)

        data = {"action": "cancel_and_restock", "_selected_action": [order.pk]}
        self.client.post(changelist, data)
        self.client.post(changelist, data)  # a second run must not restock twice

        order.refresh_from_db()
        self.small.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(self.small.stock, 3)


class StorefrontDetailTests(StoreTestCase):
    def test_add_quantity_from_product_page(self):
        self.client.post(reverse("store:add_to_cart", args=[self.small.id]), {"quantity": 2})
        self.assertEqual(self.client.session["cart"], {str(self.small.id): 2})

    def test_first_in_stock_size_is_preselected(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.context["default_variant"], self.small)
        self.assertContains(response, f'action="{reverse("store:add_to_cart", args=[self.small.id])}"')

    def test_shop_sorting_by_price(self):
        cheaper = Product.objects.create(
            name="Budget Musk", slug="budget-musk", category=self.category, description="x"
        )
        ProductVariant.objects.create(product=cheaper, volume_ml=10, price=Decimal("200"), stock=5)

        def names(sort):
            response = self.client.get(reverse("store:shop"), {"sort": sort})
            return [product.name for product in response.context["products"]]

        self.assertEqual(names("price_asc"), ["Budget Musk", "Test Oud"])
        self.assertEqual(names("price_desc"), ["Test Oud", "Budget Musk"])

    def test_home_falls_back_to_latest_when_nothing_is_featured(self):
        Product.objects.update(is_featured=False)
        self.assertContains(self.client.get(reverse("store:home")), "Test Oud")

    def test_collections_filter_by_men_women_unisex(self):
        for name, gender in (("Night Leather", "men"), ("Rose Veil", "women")):
            product = Product.objects.create(
                name=name, slug=name.lower().replace(" ", "-"), category=self.category, description="x", gender=gender
            )
            ProductVariant.objects.create(product=product, volume_ml=10, price=Decimal("300"), stock=5)

        def names(**params):
            response = self.client.get(reverse("store:shop"), params)
            return sorted(product.name for product in response.context["products"])

        self.assertEqual(names(), ["Night Leather", "Rose Veil", "Test Oud"])
        self.assertEqual(names(gender="men"), ["Night Leather"])
        self.assertEqual(names(gender="women"), ["Rose Veil"])
        self.assertEqual(names(gender="unisex"), ["Test Oud"])  # the default for existing perfumes
        self.assertEqual(names(gender="nonsense"), ["Night Leather", "Rose Veil", "Test Oud"])
        self.assertEqual(names(gender="men", q="rose"), [])

    def test_store_has_no_staff_controls(self):
        Product.objects.all().delete()
        User.objects.create_user("owner", password="owner-pass-123", is_staff=True)
        self.client.login(username="owner", password="owner-pass-123")
        response = self.client.get(reverse("store:home"))
        self.assertNotContains(response, "/dashboard/")
        self.assertNotContains(response, "Add a perfume")

    def test_rupees_filter_uses_indian_grouping(self):
        from .templatetags.store_extras import rupees

        self.assertEqual(rupees(Decimal("900")), "₹900")
        self.assertEqual(rupees(Decimal("125000")), "₹1,25,000")
        self.assertEqual(rupees(Decimal("1499.50")), "₹1,499.50")


class DashboardTests(StoreTestCase):
    def setUp(self):
        self.staff = User.objects.create_user("owner", password="owner-pass-123", is_staff=True)

    def sign_in(self):
        self.client.login(username="owner", password="owner-pass-123")

    def place_order(self):
        self.add(self.small)
        self.client.post(reverse("store:checkout"), DELIVERY)
        return Order.objects.get()

    def size_data(self, rows, initial=0):
        data = {
            "variants-TOTAL_FORMS": len(rows),
            "variants-INITIAL_FORMS": initial,
            "variants-MIN_NUM_FORMS": 1,
            "variants-MAX_NUM_FORMS": 1000,
        }
        for index, row in enumerate(rows):
            for field, value in row.items():
                data[f"variants-{index}-{field}"] = value
        return data

    def test_only_staff_can_open_the_dashboard(self):
        dashboard = reverse("store:dashboard")
        self.assertRedirects(self.client.get(dashboard), f"{reverse('store:login')}?next={dashboard}")

        User.objects.create_user("customer@example.com", password="customer-pass-123")
        self.client.login(username="customer@example.com", password="customer-pass-123")
        self.assertEqual(self.client.get(dashboard).status_code, 403)
        self.assertEqual(self.client.post(reverse("store:dashboard_product_delete", args=[self.product.pk])).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_staff_sign_in_lands_on_dashboard_and_every_page_opens(self):
        response = self.client.post(reverse("store:login"), {"email": "owner", "password": "owner-pass-123"})
        self.assertRedirects(response, reverse("store:dashboard"))
        # The store itself carries no dashboard link.
        self.assertNotContains(self.client.get(reverse("store:home")), reverse("store:dashboard"))

        order = self.place_order()
        for url in (
            reverse("store:dashboard"),
            reverse("store:dashboard_orders"),
            reverse("store:dashboard_orders") + "?status=pending&q=Test",
            reverse("store:dashboard_order", args=[order.order_number]),
            reverse("store:dashboard_products"),
            reverse("store:dashboard_product_add"),
            reverse("store:dashboard_product_edit", args=[self.product.pk]),
            reverse("store:dashboard_categories"),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_order_status_and_cancel(self):
        order = self.place_order()
        self.sign_in()
        url = reverse("store:dashboard_order", args=[order.order_number])

        self.client.post(url, {"action": "status", "status": "shipped"})
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")

        self.client.post(url, {"action": "cancel"})
        self.client.post(url, {"action": "cancel"})  # must not restock twice
        self.client.post(url, {"action": "status", "status": "delivered"})  # cancelled is final
        order.refresh_from_db()
        self.small.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(self.small.stock, 3)

    def test_add_perfume_with_sizes(self):
        self.sign_in()
        data = {
            "name": "Rose Smoke",
            "brand": "FragranSoul",
            "gender": "women",
            "category": self.category.pk,
            "description": "Rose over smoke.",
            "notes": "Rose, incense",
            "is_new": "on",
        }
        data.update(self.size_data([
            {"volume_ml": 10, "price": "450", "old_price": "", "stock": 6},
            {"volume_ml": 30, "price": "990", "old_price": "1200", "stock": 2},
        ]))
        response = self.client.post(reverse("store:dashboard_product_add"), data)
        self.assertRedirects(response, reverse("store:dashboard_products"))

        product = Product.objects.get(name="Rose Smoke")
        self.assertEqual(product.slug, "rose-smoke")
        self.assertEqual(product.gender, "women")
        self.assertEqual(product.variants.count(), 2)
        self.assertContains(self.client.get(reverse("store:shop")), "Rose Smoke")

    def test_perfume_needs_a_size_and_sizes_must_differ(self):
        self.sign_in()
        base = {"name": "No Size", "brand": "FragranSoul", "gender": "men", "category": self.category.pk, "description": "x"}

        no_sizes = dict(base, **self.size_data([{"volume_ml": "", "price": "", "old_price": "", "stock": ""}]))
        self.assertEqual(self.client.post(reverse("store:dashboard_product_add"), no_sizes).status_code, 200)

        same_size = dict(base, **self.size_data([
            {"volume_ml": 10, "price": "450", "old_price": "", "stock": 6},
            {"volume_ml": 10, "price": "500", "old_price": "", "stock": 1},
        ]))
        self.assertEqual(self.client.post(reverse("store:dashboard_product_add"), same_size).status_code, 200)
        self.assertFalse(Product.objects.filter(name="No Size").exists())

    def test_edit_perfume_updates_stock_and_removes_size(self):
        self.sign_in()
        data = {
            "name": "Test Oud Intense",
            "brand": "FragranSoul",
            "gender": "men",
            "category": self.category.pk,
            "description": "Deeper.",
            "notes": "Oud",
        }
        data.update(self.size_data([
            {"id": self.small.pk, "volume_ml": 10, "price": "550", "old_price": "", "stock": 9},
            {"id": self.large.pk, "volume_ml": 30, "price": "1200", "old_price": "1500", "stock": 0, "DELETE": "on"},
        ], initial=2))
        response = self.client.post(reverse("store:dashboard_product_edit", args=[self.product.pk]), data)
        self.assertRedirects(response, reverse("store:dashboard_products"))

        self.product.refresh_from_db()
        self.small.refresh_from_db()
        self.assertEqual(self.product.name, "Test Oud Intense")
        self.assertEqual(self.product.slug, "test-oud")  # the public URL stays the same
        self.assertEqual((self.small.price, self.small.stock), (Decimal("550"), 9))
        self.assertFalse(ProductVariant.objects.filter(pk=self.large.pk).exists())

    def test_deleting_a_perfume_keeps_past_orders(self):
        order = self.place_order()
        self.sign_in()
        self.client.post(reverse("store:dashboard_product_delete", args=[self.product.pk]))
        self.assertFalse(Product.objects.exists())
        self.assertEqual(order.items.get().product_name, "Test Oud")
        self.assertEqual(self.client.get(reverse("store:dashboard_order", args=[order.order_number])).status_code, 200)

    def test_families_add_and_delete(self):
        self.sign_in()
        families = reverse("store:dashboard_categories")
        self.client.post(families, {"name": "Amber"})
        amber = Category.objects.get(name="Amber")
        self.assertEqual(amber.slug, "amber")

        self.client.post(families, {"name": "amber"})  # duplicates are refused
        self.assertEqual(Category.objects.count(), 2)

        # A family that still has perfumes is kept, so no perfume is lost by accident.
        self.client.post(reverse("store:dashboard_category_delete", args=[self.category.pk]))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

        self.client.post(reverse("store:dashboard_category_delete", args=[amber.pk]))
        self.assertFalse(Category.objects.filter(pk=amber.pk).exists())


class ImportProductsTests(TestCase):
    HEADER = "name,category,brand,description,notes,volume_ml,price,old_price,stock,is_featured,is_new,image,gender\n"

    def run_import(self, body, **options):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "products.csv"
            path.write_text(self.HEADER + body, encoding="utf-8")
            call_command("import_products", str(path), verbosity=0, **options)

    def test_import_creates_and_updates(self):
        body = (
            "Amber Night,Amber,,Warm amber.,Amber and vanilla,10,349,,15,yes,yes,\n"
            "Amber Night,Amber,,Warm amber.,Amber and vanilla,30,799,999,5,yes,yes,\n"
        )
        self.run_import(body)
        product = Product.objects.get(slug="amber-night")
        self.assertEqual(product.brand, "FragranSoul")
        self.assertTrue(product.is_featured)
        self.assertEqual(product.variants.count(), 2)
        self.assertEqual(product.gender, "unisex")

        self.run_import("Amber Night,amber,,,,10,399,,20,,,,Women\n")
        product.refresh_from_db()
        self.assertEqual(product.gender, "women")
        with self.assertRaisesMessage(CommandError, "gender must be"):
            self.run_import("Amber Night,amber,,,,10,399,,20,,,,kids\n")
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 1)
        variant = product.variants.get(volume_ml=10)
        self.assertEqual((variant.price, variant.stock), (Decimal("399"), 20))

    def test_dry_run_and_bad_rows_save_nothing(self):
        self.run_import("Amber Night,Amber,,,,10,349,,15,,,\n", dry_run=True)
        self.assertEqual(Product.objects.count(), 0)

        with self.assertRaisesMessage(CommandError, "Line 3"):
            self.run_import("Amber Night,Amber,,,,10,349,,15,,,\nRose,Floral,,,,ten,349,,15,,,\n")
        self.assertEqual(Product.objects.count(), 0)


class PaymentTests(StoreTestCase):
    def order_with(self, method):
        self.add(self.small)
        response = self.client.post(reverse("store:checkout"), {**DELIVERY, "payment_method": method})
        return response, Order.objects.first()

    def test_checkout_offers_every_method_and_cash_is_paid_on_delivery(self):
        self.add(self.small)
        page = self.client.get(reverse("store:checkout"))
        for label in ("Cash on delivery", "UPI", "Net banking", "Credit / debit card"):
            self.assertContains(page, label)

        response, order = self.order_with("cod")
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual(order.payment_state, "Pay on delivery")
        # Cash orders have nothing to pay online.
        self.assertRedirects(self.client.get(reverse("store:pay", args=[order.order_number])), order.get_absolute_url())

    # The live site runs with DEBUG off, which leaves PAYMENTS_SANDBOX off too.
    @override_settings(PAYMENTS_SANDBOX=False)
    def test_online_methods_are_refused_without_a_gateway(self):
        response, order = self.order_with("card")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Online payment is not available yet")
        self.assertIsNone(order)

    @override_settings(PAYMENTS_SANDBOX=True)
    def test_test_payment_page_marks_the_order_paid(self):
        response, order = self.order_with("upi")
        pay = reverse("store:pay", args=[order.order_number])
        self.assertRedirects(response, pay)
        self.assertContains(self.client.get(pay), "Test payment")
        self.assertContains(self.client.get(order.get_absolute_url()), "waiting for payment")

        test = reverse("store:pay_sandbox", args=[order.order_number])
        self.assertRedirects(self.client.post(test, {"result": "failure"}), pay)
        order.refresh_from_db()
        self.assertFalse(order.is_paid)

        self.assertRedirects(self.client.post(test, {"result": "success"}), order.get_absolute_url())
        order.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(order.payment_state, "Paid online")

    def test_test_payment_is_never_available_on_the_live_site(self):
        with override_settings(PAYMENTS_SANDBOX=True):
            _, order = self.order_with("card")
        url = reverse("store:pay_sandbox", args=[order.order_number])
        with override_settings(PAYMENTS_SANDBOX=False):
            self.assertEqual(self.client.post(url, {"result": "success"}).status_code, 404)
        order.refresh_from_db()
        self.assertFalse(order.is_paid)

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="test-secret", PAYMENTS_SANDBOX=False)
    def test_gateway_payment_needs_a_genuine_signature(self):
        import hashlib
        import hmac
        from unittest import mock

        response, order = self.order_with("netbanking")
        pay = reverse("store:pay", args=[order.order_number])
        self.assertRedirects(response, pay, fetch_redirect_response=False)

        with mock.patch("store.payments.create_gateway_order", return_value="order_ABC123"):
            page = self.client.get(pay)
        self.assertContains(page, "order_ABC123")
        self.assertContains(page, "rzp_test_key")
        self.assertNotContains(page, "test-secret")

        confirm = reverse("store:pay_confirm", args=[order.order_number])
        forged = {"razorpay_order_id": "order_ABC123", "razorpay_payment_id": "pay_1", "razorpay_signature": "nope"}
        # Razorpay has no payment for the order, so the forgery is refused.
        with mock.patch("store.payments.captured_payment_id", return_value=None):
            self.assertRedirects(self.client.post(confirm, forged), pay, fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertFalse(order.is_paid)

        signature = hmac.new(b"test-secret", b"order_ABC123|pay_1", hashlib.sha256).hexdigest()
        self.assertRedirects(self.client.post(confirm, {**forged, "razorpay_signature": signature}), order.get_absolute_url())
        order.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.gateway_payment_id, "pay_1")

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="test-secret", PAYMENTS_SANDBOX=False)
    def test_payment_the_browser_never_reported_is_picked_up(self):
        from unittest import mock

        _, order = self.order_with("upi")
        pay = reverse("store:pay", args=[order.order_number])
        with mock.patch("store.payments.create_gateway_order", return_value="order_ABC123"),                 mock.patch("store.payments.captured_payment_id", return_value=None):
            self.client.get(pay)
            # Nothing has been paid yet, so the order is still waiting.
            self.assertContains(self.client.get(order.get_absolute_url()), "waiting for payment")

        # The customer paid in their UPI app and only later reopened the order.
        with mock.patch("store.payments.captured_payment_id", return_value="pay_9") as check:
            self.assertContains(self.client.get(order.get_absolute_url()), "Paid online")
            order.refresh_from_db()
            self.assertEqual((order.status, order.gateway_payment_id), ("confirmed", "pay_9"))
            # A paid order is not asked about again, and cannot be paid twice.
            check.reset_mock()
            self.assertRedirects(self.client.get(pay), order.get_absolute_url())
            check.assert_not_called()

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="test-secret", PAYMENTS_SANDBOX=False)
    def test_an_unreachable_gateway_leaves_the_order_waiting(self):
        from unittest import mock

        from store import payments

        _, order = self.order_with("card")
        Order.objects.filter(pk=order.pk).update(gateway_order_id="order_ABC123")
        with mock.patch("store.payments.captured_payment_id", side_effect=payments.PaymentError("down")):
            self.assertContains(self.client.get(order.get_absolute_url()), "waiting for payment")

    @override_settings(PAYMENTS_SANDBOX=True)
    def test_a_payment_reported_twice_is_recorded_once(self):
        from store.views import mark_paid

        _, order = self.order_with("upi")
        self.assertTrue(mark_paid(order, "pay_1"))
        self.assertFalse(mark_paid(order, "pay_2"))
        self.assertEqual(order.gateway_payment_id, "pay_1")

        # A cancelled order is never marked paid.
        _, cancelled = self.order_with("upi")
        cancelled.cancel_and_restock()
        self.assertFalse(mark_paid(cancelled, "pay_3"))
        self.assertFalse(cancelled.is_paid)

    @override_settings(PAYMENTS_SANDBOX=True)
    def test_other_visitors_cannot_pay_or_view_someone_elses_order(self):
        _, order = self.order_with("card")
        self.client.session.flush()
        other = self.client_class()
        self.assertEqual(other.get(reverse("store:pay", args=[order.order_number])).status_code, 404)
        self.assertEqual(other.post(reverse("store:pay_sandbox", args=[order.order_number]), {"result": "success"}).status_code, 404)
