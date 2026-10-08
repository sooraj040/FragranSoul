# FragranSoul — Django Perfume Store

A clean Django 6 storefront for FragranSoul. The project is intentionally delivered **without any products**. Products, images, bottle sizes, prices and stock are managed from Django Admin.

## Project structure

```text
FragranSoul/
├── fragransoul/          # Django project configuration
├── store/                 # Store application
│   ├── admin.py           # Client-friendly Admin configuration
│   ├── models.py          # Perfumes, categories, bottle-size variants and orders
│   ├── views.py           # Storefront, cart, checkout and account logic
│   ├── dashboard.py       # Staff dashboard (orders, perfumes, families)
│   ├── forms.py           # Checkout form validation
│   ├── tests.py           # End-to-end tests
│   ├── management/        # import_products command
│   ├── urls.py            # Store URLs
│   └── migrations/        # Database schema history
├── templates/             # Customer-facing HTML pages
│   └── dashboard/         # Staff dashboard pages
├── static/css/            # style.css (storefront) and dashboard.css (staff dashboard)
├── static/js/             # main.js (menu, size selection, quantity steppers)
├── media/                 # Uploaded product images
├── manage.py
└── requirements.txt
```

## Product model explained

A **Product** is the perfume itself. A **ProductVariant** is one bottle size of that perfume.

Example:

```text
Perfume: Example Fragrance
    8 ml  → ₹299 → stock 10
    10 ml → ₹349 → stock 15
    20 ml → ₹599 → stock 8
    30 ml → ₹799 → stock 5
```

The customer opens the perfume, clicks a size, and the page immediately updates the price. The selected size is what gets added to the shopping bag.

## Staff dashboard

Sign in on the store with a staff account and you are taken straight to the dashboard. It is also always available at `/dashboard/`.

- **Overview** — pending orders, order value, and bottle sizes that are running low.
- **Orders** — search and filter orders, open one to change its status or cancel it and return the items to stock.
- **Perfumes** — add, edit and delete perfumes, with their bottle sizes, prices, stock and photo.
- **Families** — add fragrance families. A family can only be deleted while it has no perfumes.

A staff account is created with `python manage.py createsuperuser`. The built-in Django admin is still available at `/admin/` and manages the same data.

## How the client adds products

The quickest way is **Dashboard → Perfumes → Add perfume**. The same can be done in the Django admin:

1. Start the server.
2. Open `/admin/`.
3. Open **Store → Categories** and create fragrance families if needed.
4. Open **Store → Perfumes → Add Perfume**.
5. Enter the perfume name, description, notes and image.
6. At the bottom of the same page, add bottle-size variants.
7. For each size enter:
   - Bottle size in ml
   - Price
   - Optional old price
   - Stock
8. Save the perfume.

No code changes are required when adding normal products.

## Adding many products at once (CSV import)

Fill in `products_template.csv` with one row per bottle size. Rows with the same perfume name become one perfume with several sizes. Required columns: `name`, `category`, `volume_ml`, `price`. The `gender` column takes `men`, `women` or `unisex` (unisex when left empty). Images named in the `image` column must already be in `media/products/`.

```powershell
python manage.py import_products products_template.csv --dry-run
python manage.py import_products products_template.csv
```

`--dry-run` checks the file without saving. Running the import again updates existing perfumes instead of duplicating them.

## Orders

1. The customer adds bottle sizes to the bag and fills in delivery details at checkout.
2. The order is saved, stock is reduced for each bottle size, and the customer sees a confirmation page with an order number.
3. Open **Admin → Store → Orders** to see new orders and change their status (Pending → Confirmed → Shipped → Delivered).
4. To cancel, select the orders and choose **Cancel selected orders and return items to stock**.

Signed-in customers can see their past orders under **Orders**. Guests can check out without an account.

Customers choose a payment method at checkout: cash on delivery, UPI, net banking or a credit / debit card. The three online methods go through Razorpay and are switched off until `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are set (see `store/payments.py`). On a developer machine without keys, a clearly marked test payment page stands in so the flow can be tried; it is never used on the live site. Shipping is controlled by `FREE_SHIPPING_THRESHOLD` and `SHIPPING_FEE` at the bottom of `fragransoul/settings.py`.

## Running the tests

```powershell
python manage.py test store
```

## Going live

Set these environment variables on the server; the built-in values are for local development only.

- `DJANGO_SECRET_KEY` — a long random string
- `DJANGO_DEBUG` — `0`
- `DJANGO_ALLOWED_HOSTS` — e.g. `fragransoul.com,www.fragransoul.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS` — e.g. `https://fragransoul.com`

Then run `python manage.py collectstatic` and have the web server serve `staticfiles/` and `media/`.

## Run the project on Windows PowerShell

```powershell
cd "D:\one team\FragranSoul"
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

- Storefront: `http://127.0.0.1:8000/`
- Dashboard: `http://127.0.0.1:8000/dashboard/`
- Admin: `http://127.0.0.1:8000/admin/`

## Important notes

- Every perfume is listed under Men, Women or Unisex (the **For** field). The store has an All tab plus one tab per collection.
- Perfumes added before this field existed are listed under Unisex.
- There are no sample/demo products.
- There is no `seed_store` command; `import_products` only loads the CSV you give it.
- Product price and stock are controlled per bottle size.
- Product cards show the cheapest available size as `From ₹...`.
- Product detail pages show every available size entered in Admin.
- The cart stores the selected bottle-size variant, so each size keeps its own price and stock.
- Checkout saves a real order and reduces stock. Payment is cash on delivery.
