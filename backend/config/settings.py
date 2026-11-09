import os
from pathlib import Path
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_files(*paths):
    """Read KEY=value lines from .env files (if present) so settings work when Django is
    started directly (runserver/gunicorn) as well as under Docker Compose.
    Variables already set in the real environment always win."""
    for path in paths:
        try:
            lines = Path(path).read_text(encoding='utf-8').splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip().removeprefix('export ').strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1]
            elif ' #' in value:
                value = value.split(' #', 1)[0].rstrip()
            if key:
                os.environ.setdefault(key, value)


# backend/.env first, then the project-root .env used by Docker Compose.
_load_env_files(BASE_DIR / '.env', BASE_DIR.parent / '.env')
DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG: SECRET_KEY = 'local-development-only-not-for-production-change-this'
    else: raise ImproperlyConfigured('DJANGO_SECRET_KEY must be configured')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,backend,172.18.99.117').split(',')
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','rest_framework','shop']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','shop.middleware.SplitSessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'shop'/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':dj_database_url.config(default=f'sqlite:///{BASE_DIR}/db.sqlite3',conn_max_age=60)}
AUTH_USER_MODEL='shop.Customer'
# Passwords: at least 10 characters (no common-password or name/email checks).
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':10}}]
LANGUAGE_CODE='en-in'
TIME_ZONE='Asia/Kolkata'
USE_I18N=True
USE_TZ=True
STATIC_URL='/static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
MEDIA_URL='/media/'
MEDIA_ROOT=Path(os.getenv('MEDIA_ROOT') or BASE_DIR/'media')  # set MEDIA_ROOT in .env to keep uploads outside the code folder
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SERVE_MEDIA=os.getenv('SERVE_MEDIA','true').strip().lower() in ('1','true','yes','on')
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default']={'BACKEND':'storages.backends.s3.S3Storage','OPTIONS':{'bucket_name':os.environ['AWS_STORAGE_BUCKET_NAME'],'region_name':os.getenv('AWS_REGION','ap-south-1'),'custom_domain':os.getenv('MEDIA_CDN_DOMAIN') or None,'querystring_auth':False,'default_acl':None,'object_parameters':{'CacheControl':'max-age=31536000, immutable'}}}
    SERVE_MEDIA=False  # files are on S3 / CDN
REDIS_URL=os.getenv('REDIS_URL','')
CACHES={'default': {'BACKEND':'django.core.cache.backends.redis.RedisCache','LOCATION':REDIS_URL}} if REDIS_URL else {'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
CELERY_BROKER_URL=REDIS_URL or 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND=CELERY_BROKER_URL
CELERY_BEAT_SCHEDULE={'expire-unpaid-orders':{'task':'shop.tasks.expire_orders','schedule':60.0},'sync-delhivery-tracking':{'task':'shop.tasks.sync_shipments','schedule':1800.0}}
REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework.authentication.SessionAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.AllowAny'],'DEFAULT_THROTTLE_CLASSES':['shop.throttles.VisitorAnonThrottle','shop.throttles.VisitorUserThrottle'],'DEFAULT_THROTTLE_RATES':{'anon':'180/min','user':'360/min','auth':'10/min'},'EXCEPTION_HANDLER':'shop.api.exception_handler'}
CSRF_TRUSTED_ORIGINS=os.getenv('CSRF_TRUSTED_ORIGINS','http://localhost:3000,http://localhost:8080').split(',')
SESSION_COOKIE_HTTPONLY=True
ADMIN_SESSION_COOKIE_NAME='admin_sessionid'  # admin login is kept separate from the customer login
CSRF_USE_SESSIONS=True  # CSRF token lives in each session, so the admin and shop logins never clash
SESSION_COOKIE_SAMESITE='Lax'
CSRF_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG
# Next.js resizes images (/_next/image) by fetching /media/… from Django over plain HTTP inside the server.
# Redirecting that internal request to https made every uploaded banner/product/collection image fail.
SECURE_REDIRECT_EXEMPT=[r'^media/']
# Token sent by the Next.js server on its own API requests (page renders, prefetches) so they are not
# rate-limited as one "visitor". Defaults to a value derived from DJANGO_SECRET_KEY, which the frontend
# container also receives from .env; set INTERNAL_API_TOKEN in .env to use your own.
import hashlib as _hl
INTERNAL_API_TOKEN=os.getenv('INTERNAL_API_TOKEN','').strip() or _hl.sha256(('aiman-internal:'+SECRET_KEY).encode()).hexdigest()
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
SECURE_HSTS_SECONDS=31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG
SECURE_HSTS_PRELOAD=not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS='DENY'
EMAIL_BACKEND=os.getenv('EMAIL_BACKEND','django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST=os.getenv('EMAIL_HOST','')
EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_USE_TLS=True
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','noreply@example.com')
DATA_UPLOAD_MAX_MEMORY_SIZE=3*1024*1024   # form fields only (files are not counted)
FILE_UPLOAD_MAX_MEMORY_SIZE=3*1024*1024   # bigger files are streamed to a temp file
DATA_UPLOAD_MAX_NUMBER_FILES=200
CASHFREE_ENVIRONMENT=os.getenv('CASHFREE_ENVIRONMENT','sandbox')
# CASHFREE_APP_ID / CASHFREE_SECRET_KEY are the standard names. In sandbox the
# CASHFREE_TEST_APP_ID / CASHFREE_TEST_SECRET_KEY names are accepted too.
_cf_test=CASHFREE_ENVIRONMENT=='sandbox'
CASHFREE_APP_ID=(os.getenv('CASHFREE_APP_ID') or (os.getenv('CASHFREE_TEST_APP_ID','') if _cf_test else '')).strip().strip('"')
CASHFREE_SECRET_KEY=(os.getenv('CASHFREE_SECRET_KEY') or (os.getenv('CASHFREE_TEST_SECRET_KEY','') if _cf_test else '')).strip().strip('"')
CASHFREE_API_VERSION=os.getenv('CASHFREE_API_VERSION','2025-01-01')
PUBLIC_SITE_URL=os.getenv('NEXT_PUBLIC_SITE_URL','http://localhost:3000').rstrip('/')
if CASHFREE_ENVIRONMENT not in ['sandbox','production']:
    raise ImproperlyConfigured('CASHFREE_ENVIRONMENT must be sandbox or production')

# Delhivery courier. Keys live only in backend/.env (never in git).
# DELHIVERY_API_TOKEN is the standard name; DELHIVERY_API_KEY is accepted too.
_env_flag=lambda name,default='': os.getenv(name,default).strip().lower() in ('1','true','yes','on')
DELHIVERY_MODE=(os.getenv('DELHIVERY_MODE') or ('sandbox' if _env_flag('DELHIVERY_SANDBOX','true') else 'production')).strip().lower()
if DELHIVERY_MODE not in ['sandbox','production']:
    raise ImproperlyConfigured('DELHIVERY_MODE must be sandbox or production')
DELHIVERY_API_TOKEN=(os.getenv('DELHIVERY_API_TOKEN') or os.getenv('DELHIVERY_API_KEY','')).strip().strip('"')
DELHIVERY_BASE_URL=(os.getenv('DELHIVERY_BASE_URL') or ('https://staging-express.delhivery.com' if DELHIVERY_MODE=='sandbox' else 'https://track.delhivery.com')).rstrip('/')
DELHIVERY_PICKUP_LOCATION=os.getenv('DELHIVERY_PICKUP_LOCATION','').strip().strip('"')
DELHIVERY_PICKUP_PINCODE=os.getenv('DELHIVERY_PICKUP_PINCODE','').strip()
DELHIVERY_PACKING_SLIP_API_URL=(os.getenv('DELHIVERY_PACKING_SLIP_API_URL') or DELHIVERY_BASE_URL+'/api/p/packing_slip').strip()
DELHIVERY_WEIGHT_GRAMS=int(os.getenv('DELHIVERY_WEIGHT_GRAMS','500'))  # per item, used when creating a shipment
DELHIVERY_SHIPPING_MODE=os.getenv('DELHIVERY_SHIPPING_MODE','Surface')
# Book the Delhivery shipment automatically when an order is paid or placed as COD.
DELHIVERY_AUTO_SHIP=_env_flag('DELHIVERY_AUTO_SHIP','true')
WHATSAPP_TOKEN=os.getenv('WHATSAPP_TOKEN','')
WHATSAPP_PHONE_ID=os.getenv('WHATSAPP_PHONE_ID','')
WHATSAPP_OTP_TEMPLATE=os.getenv('WHATSAPP_OTP_TEMPLATE','')
WHATSAPP_GRAPH_VERSION=os.getenv('WHATSAPP_GRAPH_VERSION','')
# Calendly personal access token (Calendly → Integrations → API & Webhooks). Optional: with it, the
# booked date/time and attendee are fetched and shown under My Account → Appointments.
CALENDLY_TOKEN=os.getenv('CALENDLY_TOKEN','').strip().strip('"')
# Continue with Google (OAuth). Keys live only in backend/.env. The redirect URI must be added in
# Google Cloud Console → Credentials → your OAuth client → Authorised redirect URIs.
GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID','').strip().strip('"')
GOOGLE_CLIENT_SECRET=os.getenv('GOOGLE_CLIENT_SECRET','').strip().strip('"')
GOOGLE_REDIRECT_URI_SET=bool((os.getenv('GOOGLE_REDIRECT_URI') or '').strip())
GOOGLE_REDIRECT_URI=(os.getenv('GOOGLE_REDIRECT_URI') or PUBLIC_SITE_URL+'/api/auth/google/callback/').strip()
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']=['shop.security.SafeSessionAuthentication']
REST_FRAMEWORK['EXCEPTION_HANDLER']='shop.security.exception_handler'

PASSWORD_RESET_TIMEOUT=3600
EMAIL_TIMEOUT=10
