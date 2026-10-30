# Homepage and authentication update

The homepage now follows the supplied October 30 reference's section order: wide palace hero with live headline, collection cards, occasion categories, four-card product rows, confidence strip, wedding mosaic, campaign banner, style strip, service benefits, signature products, fitting consultations and designer notes. The footer uses burgundy. Mobile grids collapse to two columns; consultation cards stack.

Product cards retain database prices, images and links. Existing catalogue photography is used; it is not identical to every photograph in the reference. Editorial category tiles resolve matching active collections or a catalogue search. Promotional guarantees and percentage discounts in the mockup have not been represented as real store policies. Custom admin hero uploads still override the bundled hero.

`frontend/public/images/home-hero.webp` is a 251 KiB generated campaign image. Built-in imagegen prompt: “Text-free wide 3:1 palace fashion photograph matching the reference hero: two adult women on the right in burgundy and ivory embroidered lehengas, warm cream sandstone architecture, empty left space for the live headline.” It is illustrative campaign imagery, not a product photograph.

## Authentication fix

Next.js automatically canonicalized trailing slashes, and the external rewrite also removed the slash before proxying to Django. Django redirected `/api/csrf` back to `/api/csrf/`, creating a redirect loop before signup or login could submit. Disable Next's automatic slash redirects and preserve a trailing slash in the API/account/admin rewrite destinations. Media and static asset URLs retain file paths.

Registration now includes password confirmation and explains the existing password requirements. Switching authentication modes clears an old OTP challenge. Successful authentication accepts same-origin `next` or legacy `redirect` destinations and rejects external URLs. CSRF enforcement is retained. WhatsApp still requires configured provider credentials.

## Validation

- Next.js production build and TypeScript check passed.
- All 24 existing Django tests passed using SQLite locally.
- `python3 scripts/check_auth.py` passed against a running production frontend and Django server with a disposable database: CSRF enforcement, registration, session persistence, logout, rejection of an incorrect password, successful login, and homepage/auth/hero HTTP responses.
- The proxy smoke test is included in frontend CI after the build.
- Browser visual and click-through validation remain pending: the environment could not download Chromium. Pixel-level matching and mobile rendering are not verified.

## Deployment

Rebuild/redeploy the frontend to apply `next.config.ts` and bundled images. There are no database migrations or Cashfree changes. For Docker: `docker compose build frontend` then `docker compose up -d frontend`. Keep the deployed HTTPS hostname in `CSRF_TRUSTED_ORIGINS` and `ALLOWED_HOSTS`, as described in the existing deployment guide. Verify signup/login and desktop/mobile layout on staging before production.
