"""Public URL routes for the FragranSoul storefront."""

from django.urls import path

from . import dashboard, views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:variant_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:variant_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:variant_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:order_number>/", views.order_detail, name="order_detail"),
    path("account/orders/", views.order_history, name="order_history"),
    path("account/login/", views.account_login, name="login"),
    path("account/register/", views.account_register, name="register"),
    path("account/logout/", views.account_logout, name="logout"),
    # Staff dashboard (the built-in Django admin stays at /admin/).
    path("dashboard/", dashboard.overview, name="dashboard"),
    path("dashboard/orders/", dashboard.orders, name="dashboard_orders"),
    path("dashboard/orders/<str:order_number>/", dashboard.order, name="dashboard_order"),
    path("dashboard/perfumes/", dashboard.products, name="dashboard_products"),
    path("dashboard/perfumes/add/", dashboard.product_edit, name="dashboard_product_add"),
    path("dashboard/perfumes/<int:pk>/", dashboard.product_edit, name="dashboard_product_edit"),
    path("dashboard/perfumes/<int:pk>/delete/", dashboard.product_delete, name="dashboard_product_delete"),
    path("dashboard/families/", dashboard.categories, name="dashboard_categories"),
    path("dashboard/families/<int:pk>/delete/", dashboard.category_delete, name="dashboard_category_delete"),
]
