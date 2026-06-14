# Sciadè Store

Prototype e-commerce for Sciadè, split into frontend and backend.

## Structure

- `frontend/`: customer pages, admin pages, CSS, browser JavaScript, images
- `backend/`: Python server, API routes, login/session handling
- `data/`: local SQLite database for orders, products, and users

## Run locally

From this folder:

```bash
SCIADE_ADMIN_EMAIL="lv.desideri@gmail.com" SCIADE_ADMIN_PASSWORD="scegli-una-password" python3 backend/server.py
```

Then open:

- Shop: http://localhost:4176
- Checkout: http://localhost:4176/checkout.html
- Admin login: http://localhost:4176/login.html
- Orders: http://localhost:4176/admin.html

## Admin features

The admin area is password protected. From `admin.html` you can:

- view saved checkout orders
- remove completed orders
- add products to the catalog
- edit existing products
- remove sold products
- upload product images

Products are stored in the SQLite database and loaded by the public shop through
`/api/products`.

Customers can create their own account from `login.html` with email and password.

## Pre-publishing configuration

For an online deployment, set these environment variables on the hosting service:

```bash
SCIADE_ENV="production"
SCIADE_ADMIN_EMAIL="your-admin-email@example.com"
SCIADE_ADMIN_PASSWORD="a-long-private-password"
SCIADE_COOKIE_SECURE="1"
```

When `SCIADE_ENV=production`, the server refuses to start unless the admin email
and password are explicitly provided. Do not publish the site with the temporary
local password.

Render provides the public port through `PORT`; the server reads it
automatically. In production, the server listens on `0.0.0.0` by default.

## First Render deploy checklist

1. Create a GitHub repository, for example `sciade-store`.
2. Commit and push this folder to that repository.
3. In Render, choose `New` -> `Web Service`.
4. Connect the GitHub repository.
5. Use these commands if Render asks for them manually:

```bash
Build Command: pip install -r requirements.txt
Start Command: python3 backend/server.py
```

6. Add these environment variables in Render:

```text
SCIADE_ENV=production
SCIADE_COOKIE_SECURE=1
SCIADE_ADMIN_EMAIL=lv.desideri@gmail.com
SCIADE_ADMIN_PASSWORD=your-real-admin-password
```

The free Render version is useful for a public demo. It is not yet the final
storage setup for a real shop because local uploaded files and SQLite data can
be lost on redeploys or server restarts.

## Security notes in the current prototype

- SQL queries use SQLite parameters instead of string interpolation.
- Passwords are stored as salted PBKDF2-SHA256 hashes, not as plain text.
- Admin login attempts are rate-limited by admin email and IP.
- Session cookies are `HttpOnly`, `SameSite=Lax`, and can be marked `Secure`.
- The backend recalculates checkout totals from the product database instead of
  trusting prices sent by the browser.
- Basic security headers are sent with every response.

## Future publishing notes

Before accepting real payments, add HTTPS through the hosting provider, database
backups, payment integration through Stripe or PayPal, and do not store card
details in this database.
