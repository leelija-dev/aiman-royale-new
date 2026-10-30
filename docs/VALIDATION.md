# Validation record — 30 October 2026

## Passed in this workspace

- Next.js production build, including TypeScript compilation: passed. All application/page routes plus robots and sitemap generated/registered successfully.
- Django system checks: no issues.
- Migration drift check: no model changes missing from migrations.
- Django static collection: passed (154 source static files, compressed/manifest post-processing).
- 24 automated Django tests passed on the development SQLite test database:
  - Server-calculated order amount and stock deduction.
  - Checkout request idempotency.
  - Rejection of insufficient stock and transaction rollback.
  - One-time release of expired reservations.
  - Captured payment handling and replay safety.
  - Rejection of mismatched payment amounts.
  - Late payment reconciliation state after stock release.
  - Unconfigured payment rejection without clearing the cart.
  - Cross-customer order isolation.
  - CSRF on anonymous and authenticated cart mutations.
  - Single active booking per appointment slot.
  - Persisted OTP failures and lockout.
  - Signed webhook handling, invalid-signature rejection and replay.
  - Password-reset page rendering and email generation.
  - Draft policy exclusion.
  - Invalid cart quantity rejection.
  - Guest cart merge during email registration.
  - Checkout API ignores a supplied client total and reuses its provider order (mocked gateway).
  - Unconfigured WhatsApp fails closed.
- All 12 frontend WebP assets decoded successfully.
- Source ZIP integrity and exclusion of runtime secrets, installed dependencies, test databases and generated runtime output checked during packaging.

## Not verified here

- Browser visual/mobile interaction checks. The managed preview launcher appended Vite-specific `--host` and `--strictPort` flags to the Next.js dev command, which Next.js rejected. No substitute browser environment was started. Exact PNG parity, mobile overflow, keyboard navigation and interactive Cashfree rendering need staging browser review.
- Actual Docker image/Compose execution: Docker was unavailable here.
- PostgreSQL concurrency, load, soak and failure tests. The included CI workflow targets PostgreSQL, but has not run on the user's repository. SQLite tests do not validate row-lock concurrency behaviour.
- AWS deployment, RDS backups/restoration, object storage/CDN and Redis/Celery operations under production conditions.
- Real Cashfree, Meta WhatsApp and SMTP delivery. No provider credentials were supplied; no live transactions/messages were sent.
- Lighthouse/Core Web Vitals or any traffic-capacity/ranking target.

## Required before public launch

Configure a separate staging environment and providers; replace demo catalogue/stock with verified data; publish approved policies and fit guidance; use original high-resolution editorial images; compare every route against the supplied desktop/mobile references; exercise test-mode checkout and actual message delivery; run PostgreSQL concurrent-checkout/slot tests, an appropriate load profile, and a backup restore drill. See DEPLOYMENT.md and INTEGRATIONS.md.

## Cashfree update checks

The production Next.js build and all 24 Django tests passed after replacing the payment integration. Additional tests cover authenticated Cashfree order/payment lookup, rejection of browser-claimed success, provider amount mismatch, repeated raw-body-signed notifications, body tampering, timeout retries retaining the same provider order and idempotency key, and cross-customer verification rejection. Provider responses were mocked; no sandbox or live Cashfree transaction was executed. Browser/real SDK verification remains required on a whitelisted staging domain.
