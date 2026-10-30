# Deploy as a separate AWS website

The archive contains runnable application containers and local Compose orchestration. It does **not** create AWS resources or contain Terraform/CloudFormation provisioning. No AWS account, domain, database, merchant account or messaging account was modified.

## Recommended staging topology

Use a new staging hostname, a new database and a separate S3 media bucket. Do not point this project at the Laravel database or replace the live aimanroyale.com DNS while reviewing it.

- ECS/Fargate: separate frontend, Django and Celery worker services; exactly one beat scheduler.
- RDS PostgreSQL: private subnets, encrypted storage, automated backups, monitored connections.
- Managed Redis-compatible service: private access and TLS/auth where required, with the configured Redis URL available to Django, worker and beat.
- ALB: HTTPS listener with ACM certificate, public host restricted to your intended new domain.
- S3 + CloudFront: product media; immutable unique object names, origin access control, a dedicated CDN hostname.
- ECR: versioned frontend/backend images.
- Secrets Manager: Django secret, database password/URL, payment secrets, WhatsApp credentials and SMTP credentials. Prefer task roles to embedded AWS access keys.

## Route requests

ALB path rules send `/api/*`, `/admin/*`, `/accounts/*` and `/static/*` to Django; all other paths to Next.js. Media image URLs use the CDN directly. WhiteNoise serves collected Django static assets.

Only the trusted ALB/private frontend service may reach Django. The ALB must overwrite/maintain a trusted `X-Forwarded-Proto: https`; never expose Django's container port publicly. `SECURE_PROXY_SSL_HEADER` trusts that header. Configure the target security group accordingly.

Next.js server-side reads use `INTERNAL_API_URL` to reach Django over the private network, with `INTERNAL_REQUEST_SCHEME=https` so Django recognises the externally secure request. Next's built-time rewrites also use the internal backend URL, so set the correct service-discovery hostname when building. Direct browser API calls normally route through the ALB to Django.

## Production settings

- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY`: unique, high-entropy secret, never the sample value.
- `ALLOWED_HOSTS`: public new hostname plus the exact trusted internal service hostname(s) and health-check host requirements. Avoid `*`.
- `CSRF_TRUSTED_ORIGINS`: exact HTTPS public origin(s).
- `NEXT_PUBLIC_SITE_URL`: canonical public HTTPS origin, both at build and runtime.
- `INTERNAL_API_URL`: private Django service URL, both at build and runtime.
- `INTERNAL_REQUEST_SCHEME=https`
- `DATABASE_URL`: RDS PostgreSQL URL with required SSL settings (`?sslmode=require` at minimum; use full certificate verification where configured).
- `REDIS_URL`: the managed service URL, with correct database, authentication and TLS options.
- `AWS_STORAGE_BUCKET_NAME`, `AWS_REGION`, `MEDIA_CDN_DOMAIN`.
- All integration settings described in `INTEGRATIONS.md`.

Secure session/CSRF cookies, HTTPS redirection and HSTS turn on when debug is off. Public health checks must supply the expected Host and trusted HTTPS forwarding header; otherwise they can receive a redirect or rejected-host response. The current `/api/health/` checks process availability, not downstream database/Redis health; add infrastructure-level dependency monitoring separately.

## Release sequence

1. Build and push versioned container images after CI passes. The local Docker build was not executed in the delivery environment; verify it in staging.
2. Configure the new RDS, Redis and S3 resources; store secrets. Create service definitions with appropriate CPU/memory, log groups, security groups and health checks.
3. Run `python manage.py migrate` as a one-off backend task. The included backend Dockerfile collects Django static files during the image build using nonproduction build settings. Keep those files in the serving image; a separate one-off task's filesystem is not shared with service tasks.
4. Create an admin through a controlled one-off task. Do not install demo stock into production. Import/enter verified catalogue data and actual availability.
5. Start backend, worker, beat and frontend, then configure the ALB rules and new hostname. Restrict staging to reviewers and prevent indexing until approved.
6. Publish approved policies and size guidance. Verify contact numbers, prices, stock, images, fit promises, delivery/returns terms and tax treatment.
7. Exercise actual provider test-mode purchase/verification, failed payment, appointment booking and WhatsApp/email delivery. Test mobile pages in a browser against the supplied references.
8. Run load and concurrency tests against staging PostgreSQL. Configure alerts, backup retention, restore drills and operator access before live payment activation.

## Cache and performance

Only cache public assets at the CDN. Do not cache authenticated HTML or `/api/auth`, cart, checkout, orders, wishlist and appointment writes. Catalogue currently reads the database on each request so stock visibility is current; Redis backs shared API throttling and Celery. Public catalogue caching with explicit invalidation can be introduced after query profiling. Occasion filtering currently uses a portable application-level JSON filter and should be converted to indexed PostgreSQL JSON/search filtering for a large catalogue.

The included catalogue is small. No high-concurrency benchmark was performed, and no traffic capacity guarantee is inferred from using AWS or Redis.

## Operations and recovery

- Keep at least daily database backups and versioned media; verify a restore into a separate environment.
- Log request errors, worker failures and order/provider references. Avoid logging OTP codes, tokens, addresses or measurement payloads.
- Alert on payment mismatches, `refund_required`, pending reservations older than 35 minutes, queue delay, 5xx rates and database saturation.
- Keep exactly one beat scheduler. Worker restart must not lose PostgreSQL order state.
- Roll back application images by immutable tag; back up before schema migrations and assess backward compatibility. Do not automatically reverse migrations with customer data.
- Maintain provider reconciliation procedures. The admin intentionally does not let staff mark arbitrary pending orders as paid.

Official deployment references:
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://nextjs.org/docs/app/guides/production-checklist
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
