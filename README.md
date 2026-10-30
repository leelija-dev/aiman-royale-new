# Aiman Royale — separate ecommerce website (v1.1, Cashfree)

A new, independently runnable Aiman Royale storefront and commerce backend, based on the supplied ivory/burgundy luxury fashion references. This project does not connect to or change the existing Laravel application, database, customers or orders.

Cashfree upgrade instructions and required environment settings are in `docs/INTEGRATIONS.md`. Run the new database migration when updating from v1.0.

## What is included

- Next.js App Router + React + TypeScript storefront with responsive custom CSS, serif typography and the supplied visual direction.
- Homepage, searchable product listing, collection pages with **Haldi / Wedding / Party / Festive** filtering, product details, size/colour selection, custom fitting measurements, wishlist, cart, checkout, email registration/login, WhatsApp OTP flow, customer orders, appointment requests and policy pages.
- Django REST Framework APIs, PostgreSQL-ready migrations and Django admin for products, photos, variants, stock, collections, prices, coupons, site settings, orders, appointment slots and policies.
- Session authentication and CSRF protection, server-calculated totals, stock reservations, idempotent checkout, server-side Cashfree verification and signed webhooks, and expiry/release of unpaid stock through Celery.
- WhatsApp Cloud API authentication-template adapter; code expiry, hashed codes, retry limits and throttling. WhatsApp chat links use the configurable store number.
- PostgreSQL, Redis, Celery worker/beat, Next.js, Django and Nginx Docker Compose setup; CI workflow; AWS deployment instructions.
- Server-rendered catalogue pages, product JSON-LD, canonical URLs, dynamic XML sitemap, robots rules, page metadata and modern responsive image delivery.

## Important delivery status

This is a source-code implementation for staging, **not a deployed or launch-certified shop**. Core builds and automated tests are recorded in `docs/VALIDATION.md`. Browser visual QA was blocked by the available preview launcher. Pixel-perfect parity with the reference PNGs has therefore not been verified.

Products, prices, descriptions and stock from `seed_store` are **demonstration data**, not a live inventory import. Product photography was obtained from the existing Aiman Royale catalogue; editorial crops come from the supplied PNGs. Review every product, image, price, fabric, stock level and public claim before publishing. The first release uses custom CSS instead of the architecture document's suggested Tailwind/component library. It preserves the requested Next.js/Django/PostgreSQL/Redis/Celery architecture.

This is a **single-brand store**. The architecture attachment's longer-term marketplace seller/commission/settlement platform, automated carrier booking, automated returns/refunds, loyalty and recommendation systems are not implemented. OpenSearch is deliberately deferred. No million-user capacity or search ranking claim is made.

## Quick start with Docker

Requirements: Docker Engine/Desktop with Compose v2; available local port 8080.

```sh
cp .env.example .env
# Edit .env: choose a unique DJANGO_SECRET_KEY and matching POSTGRES_PASSWORD / DATABASE_URL.
docker compose build
docker compose up -d db redis
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py collectstatic --noinput
docker compose run --rm backend python manage.py seed_store --demo-slots
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d
```

Open **http://localhost:8080**. Admin: **http://localhost:8080/admin/** using the account you created. No default admin password is supplied.

The optional `--demo-slots` creates example appointment availability for the following 14 days, in IST. Remove those slots and enter actual studio availability before taking bookings. Seeding is non-destructive and does not overwrite edited products. It is not a production migration/import tool.

Local Docker binds only to loopback. `DJANGO_DEBUG=1` is only for local development; do not expose this configuration publicly. Production requires HTTPS and the settings in `docs/DEPLOYMENT.md`.

## Run without Docker (development)

Python 3.12+, Node 24 and npm are used by this package. A development-only SQLite database is used if `DATABASE_URL` is omitted. PostgreSQL is required for deployment and concurrent checkout correctness.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
export DJANGO_DEBUG=1
python backend/manage.py migrate
python backend/manage.py seed_store --demo-slots
python backend/manage.py createsuperuser
python backend/manage.py runserver 127.0.0.1:8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Visit http://localhost:3000. Next.js proxies API, media, admin and password-reset routes to Django. For local task processing, run Redis and, from `backend/`, `celery -A config worker -l info` and `celery -A config beat -l info`. These need the same environment as Django. Without beat, unpaid order reservations will not be released automatically.

## Configure integrations

See `docs/INTEGRATIONS.md` for exact settings and verification steps. No payment, WhatsApp, SMTP or AWS credentials are included. Configure secrets in the server environment or your secret manager; never commit `.env`.

- **Payments:** Cashfree adapter, with UPI/cards/netbanking/wallet options supplied by the provider. Merchant onboarding and production activation are separate requirements. Test mode must be completed before live keys.
- **WhatsApp:** Meta Cloud API, a registered sending number and an approved authentication template. OTP appears in the UI only when its settings are present. Template/account delivery approval must be tested.
- **Email:** SMTP for password-reset messages. Newsletter signups are stored; campaign sending is not included.
- **Shipping:** Admin-configured flat rate/free-shipping threshold. Tracking URLs are entered by staff. No courier API is assumed.
- **Appointments:** A slot is reserved as `requested`; staff confirm it and contact the customer. Video links and outbound appointment reminders are managed manually in this release.

## Store management

1. Set brand contact details, announcement, hero copy/image, shipping costs and COD setting under Site Settings. COD is off by default.
2. Add collections and products, assign occasions as a JSON list such as `["Wedding", "Party"]`, and add each size/colour variant with its actual stock.
3. Upload original, high-quality product images. Next Image produces responsive WebP/AVIF delivery; the original is retained in media/object storage. Use meaningful alternative text. Avoid upscaling low-resolution source imagery.
4. Publish your approved Terms, Privacy, Shipping, Returns and Size Guide under Pages with slugs `terms`, `privacy`, `shipping`, `returns`, `size-guide`. Seeded drafts are intentionally unpublished; their links return 404 until approved content is published.
5. Create Appointment Slots in IST; manage requests in Appointments. A slot cannot have two active bookings.
6. Order admin actions move paid/COD orders to processing, then shipped after a tracking URL is entered, then delivered. Financial fields are read-only. Payment reconciliation and refunds require the operational procedure in the integrations guide.

Homepage secondary editorial photographs/headings and navigation remain in React source. The hero, announcements, contacts, product/collection catalogue, pricing, stock, orders, policies and slots are database-driven. This is not a drag-and-drop page builder.

## Checks

```sh
DJANGO_DEBUG=1 python backend/manage.py test shop
DJANGO_DEBUG=1 python backend/manage.py makemigrations --check --dry-run
cd frontend
npm run build
```

The provided GitHub Actions workflow runs backend tests against PostgreSQL and builds the frontend. It has not been executed on your GitHub account. See `docs/VALIDATION.md` for the checks actually run here.

## Layout

- `frontend/` — pages, reusable components, styles, optimised seed assets.
- `backend/` — API, database models/migrations, services, tasks, admin, tests and seed assets.
- `deploy/` — local Nginx entrypoint.
- `compose.yaml` — independent local stack.
- `docs/` — configuration, deployment, validation and design notes.

Keep customer measurements, addresses and contact information within the store's access/retention policy. Restrict staff access through Django permissions. Back up PostgreSQL and media together; test restoration before launch.
