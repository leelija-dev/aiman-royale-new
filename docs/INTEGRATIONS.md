# Integration and operating guide

## Cashfree Payments (v1.1 update)

Cashfree replaces the previous Razorpay integration for new orders. Credentials stay in Django; the browser receives only the payment session ID and sandbox/production mode.

### Required configuration

```dotenv
CASHFREE_APP_ID=your_cashfree_app_id
CASHFREE_SECRET_KEY=your_cashfree_secret_key
CASHFREE_ENVIRONMENT=sandbox
CASHFREE_API_VERSION=2025-01-01
NEXT_PUBLIC_SITE_URL=https://your-new-staging-domain.example
```

The API version is explicitly pinned. Sandbox uses `https://sandbox.cashfree.com/pg`; production uses `https://api.cashfree.com/pg`. Do not mix credentials between environments. There is no separate webhook secret in this implementation: signature verification uses the Cashfree client secret associated with that environment.

1. Obtain sandbox Payment Gateway credentials from your Cashfree merchant dashboard and set the backend environment variables above. Restart backend and workers.
2. Whitelist the new storefront domain in Cashfree for hosted web checkout. `NEXT_PUBLIC_SITE_URL` must point to that storefront; Cashfree returns users to `/payment/return?order=<application UUID>`.
3. Configure the Cashfree webhook URL as `https://YOUR-NEW-DOMAIN/api/payments/webhook/`, including the trailing slash, and enable payment success events (`PAYMENT_SUCCESS_WEBHOOK`). Other validly signed event types are acknowledged without marking an order paid.
4. Run a sandbox purchase through UPI/card methods available for your account. Verify success, cancellation, failed attempts, delayed success, repeated callbacks, raw-body tampering and incorrect totals. Confirm the provider order against your application order and actual inventory.
5. After merchant activation and staging acceptance, use production credentials and set `CASHFREE_ENVIRONMENT=production`. Configure the production webhook and approved live domain separately. Never paste secret keys into chat or frontend code; enter them in your server environment/secret manager.

### Checkout and verification

The frontend loads Cashfree's v3 JavaScript SDK and opens hosted checkout in a modal. Redirect fallback uses the payment-return route. Completion of the SDK promise alone does not mean payment success.

The authenticated verification endpoint fetches the order from Cashfree, checks the exact order ID, INR currency and stored server-calculated total, requires `order_status=PAID`, then fetches payments and requires a matching `SUCCESS` payment before marking the local order paid. Accounts expose a Check payment status link. The browser cannot supply a trusted amount, status or payment identifier.

Webhooks verify Base64 HMAC-SHA256 over the exact timestamp-header bytes followed by the raw HTTP body, then re-query authenticated Cashfree APIs. Do not put middleware in front of the endpoint that rewrites JSON bodies. Provider errors return a failure status so Cashfree can retry. Repeated successful callbacks do not deduct inventory or fulfil again. Timestamp is signed but no local short age limit is imposed, allowing legitimate delayed delivery/retries; database state changes are idempotent.

### Retries and stock

Each order stores `ar_<UUID without hyphens>` before the provider request. Cashfree create-order calls send the same UUID `x-idempotency-key` and payload on retry. A timeout therefore keeps the local reference rather than starting a second reservation/provider order. Retrying the same open checkout page reuses the stored payment session.

Pending stock is reserved for 30 minutes. Celery beat expires unpaid reservations and restores stock once. Late successful payment after release produces `refund_required`, never automatic fulfilment. Customers should check status/contact the studio before another purchase if already charged. After leaving the checkout page, payment status can be rechecked, but creating a fresh payment session from account history is not implemented.

Do not enable Cashfree service-fee/surcharge collection for this release: verification deliberately requires payment amount to equal the order total exactly. Partial payments, subscriptions, provider offers changing collected amount, automated refunds and automated returns are not included.

### Upgrade from v1.0

Back up first, replace the application source, configure Cashfree settings, and run `python manage.py migrate`. Migration 0002 adds the private session field and changes the default for **new** orders. Existing order IDs, prices and payment methods are preserved. Existing Razorpay transactions are not converted to Cashfree. If v1.0 has active real transactions, complete/reconcile them using its original provider/webhook service before switching traffic; this release does not retain the Razorpay callback handler.

Refunds and cancellations after payment remain manual operations through authorised store/provider processes. Never ship pending, expired, cancelled or refund-required orders. Financial fields remain read-only in admin.

Official references:
- https://www.cashfree.com/docs/payments/online/web/redirect
- https://www.cashfree.com/docs/api-reference/payments/latest/orders/create-order
- https://www.cashfree.com/docs/api-reference/payments/latest/payments/get-payments-for-an-order
- https://www.cashfree.com/docs/payments/online/webhooks/signature-verification

## WhatsApp OTP and chat

Environment: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_OTP_TEMPLATE`, `WHATSAPP_GRAPH_VERSION`.

Use an approved authentication template with an English (`en_US`) body code parameter and a copy-code URL button at index 0, matching the payload in `shop/services.py`. Set a currently supported Graph API version from your Meta app dashboard. Supply the phone-number ID, not the human-readable telephone number. Use a suitably scoped system-user token in the server's secret manager.

OTP codes expire after five minutes, are stored as password hashes, and allow at most five attempts. Requests are throttled by IP and phone. Codes never appear in an API response or development log. Delivery failures do not authenticate a customer. The separate email/password registration flow remains available without WhatsApp.

Test with your approved recipient accounts, consent wording and template, including expired codes, resend limits and failed delivery. This environment did not send any actual WhatsApp messages. WhatsApp-only customers have unusable email passwords; they sign in with OTP. Automatic merging of phone accounts with existing email accounts is intentionally not performed.

The chat button uses the store phone configured in Site Settings and opens WhatsApp. It is not an AI chatbot. Order status and promotional broadcast templates are not implemented.

## Email

Set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`. TLS is enabled. Password-reset links use the public request host; configure the reverse proxy correctly. Use an authorised sender and configure domain authentication with your mail provider. SMTP is not silently simulated when absent.

## Media

Local Docker uses a media volume. Production uses `AWS_STORAGE_BUCKET_NAME`, `AWS_REGION`, and `MEDIA_CDN_DOMAIN`; give the backend a least-privilege AWS IAM task role. Configure a private S3 bucket with CloudFront origin access control and a public media CDN hostname. Do not store customer documents in this public product-media bucket. `querystring_auth=False` is for public catalogue imagery delivered by the CDN.

Pass `MEDIA_CDN_DOMAIN` both at frontend build time (Next Image allowlist) and backend runtime. Seed/demo web assets are WebP; original product uploads are preserved. Next Image creates AVIF/WebP variants and responsive sizes on demand. Do not send oversized original files for grid cards.
