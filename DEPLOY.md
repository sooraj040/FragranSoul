# Putting FraagranSoul live on fragransoul.in (PythonAnywhere)

This guide takes the site from your computer to `https://www.fragransoul.in`.
Do the steps in order. Wherever you see `USERNAME`, type your PythonAnywhere username.

PythonAnywhere's button names change from time to time. If a label is slightly
different from what is written here, look for the closest match on the same page.

## What you need

- The file `fraagransoul_deploy.zip` (in the `FraagranSoul_client_ready` folder).
- A PythonAnywhere account on a **paid plan**. The free plan cannot use your own domain.
- Access to the DNS settings of `fragransoul.in` at your domain provider.

## 1. Upload the project

1. Sign in at pythonanywhere.com and open the **Files** tab.
2. Upload `fraagransoul_deploy.zip` into `/home/USERNAME/`.
3. Open the **Consoles** tab and start a **Bash** console. Run:

```bash
cd ~
unzip fraagransoul_deploy.zip
ls FraagranSoul        # you should see manage.py
```

## 2. Install Python packages

In the same Bash console:

```bash
mkvirtualenv fraagransoul --python=python3.13
cd ~/FraagranSoul
pip install -r requirements.txt
```

If `python3.13` is not available, use `python3.12`. Django 6 needs Python 3.12 or newer.

## 3. Create the settings file

```bash
cd ~/FraagranSoul
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
nano .env
```

The `python -c` line prints a long random string. In the editor, replace
`replace-me` after `DJANGO_SECRET_KEY=` with that string. Leave the other lines
as they are. Save with **Ctrl+O**, **Enter**, then exit with **Ctrl+X**.

## 4. Create the database and the owner account

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

`createsuperuser` asks for a username and password. This is the account that
signs in on the site and lands on the dashboard. The live site starts with an
empty database: no perfumes, no orders.

## 5. Create the web app

1. Open the **Web** tab and choose **Add a new web app**.
2. For the domain, enter `www.fragransoul.in`.
3. Choose **Manual configuration** (not "Django"), then the same Python version as in step 2.
4. On the web app page, fill in:
   - **Source code:** `/home/USERNAME/FraagranSoul`
   - **Working directory:** `/home/USERNAME/FraagranSoul`
   - **Virtualenv:** `/home/USERNAME/.virtualenvs/fraagransoul`
5. Click the **WSGI configuration file** link. Delete everything in it and paste:

```python
import os
import sys

path = "/home/USERNAME/FraagranSoul"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "fraagransoul.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

   Replace `USERNAME`, then save.

6. Under **Static files**, add two rows:

| URL        | Directory                                  |
|------------|--------------------------------------------|
| `/static/` | `/home/USERNAME/FraagranSoul/staticfiles`  |
| `/media/`  | `/home/USERNAME/FraagranSoul/media`        |

7. Click the green **Reload** button.

## 6. Point the domain at the site

1. On the **Web** tab, find the DNS setup section. It shows a value like
   `webapp-123456.pythonanywhere.com`. Copy it.
2. In your domain provider's DNS settings for `fragransoul.in`, add:

| Type  | Name  | Value                                  |
|-------|-------|----------------------------------------|
| CNAME | `www` | `webapp-XXXXXX.pythonanywhere.com`     |

   If a `www` record already exists (often a "parked" page), delete it first.

3. Make the bare domain forward to the `www` address: in the domain provider's
   panel, set up a redirect from `fragransoul.in` to `https://www.fragransoul.in`.
   PythonAnywhere serves the `www` address only; its help page on "naked domains"
   lists other ways to do this.

DNS changes can take from a few minutes to a few hours to spread.

## 7. Turn on HTTPS

Once `www.fragransoul.in` opens the site:

1. On the **Web** tab, in the **Security** section, choose the
   **auto-renewing Let's Encrypt certificate**.
2. Turn on **Force HTTPS**.
3. Click **Reload**.

Sign-in only works over HTTPS on the live site, so do this step before testing accounts.

## 8. Check the live site

- `https://www.fragransoul.in/` shows the home page with its styling.
- Sign in with the account from step 4. You land on the dashboard.
- Add a fragrance family, then a perfume with a photo. The photo shows in the store.
- Place a test order, then find it under **Orders** in the dashboard and cancel it.

## Updating the site later

Upload the changed files (or a new zip, unzipped over the old folder), then in a Bash console:

```bash
workon fraagransoul
cd ~/FraagranSoul
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

and click **Reload** on the Web tab. Do not overwrite `db.sqlite3`, `media/` or
`.env` on the server: they hold the live orders, photos and secret key.

## Backups

Everything that matters is in two places on the server: the file
`~/FraagranSoul/db.sqlite3` (perfumes, orders, accounts) and the folder
`~/FraagranSoul/media/` (photos). Download both from the **Files** tab regularly.

## If something goes wrong

- **"Something went wrong" page:** open the **error log** link on the Web tab. The last lines say what failed.
- **Page has no styling:** the `/static/` row in step 5 is wrong, or `collectstatic` was not run.
- **"Bad Request (400)":** the address you opened is not listed in `DJANGO_ALLOWED_HOSTS` in `.env`.
- **Sign-in or checkout says "CSRF verification failed":** the site is being opened over `http://`. Finish step 7.
