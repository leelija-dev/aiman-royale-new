import os
from pathlib import Path
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG: SECRET_KEY = 'local-development-only-not-for-production-change-this'
    else: raise ImproperlyConfigured('DJANGO_SECRET_KEY must be configured')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,backend').split(',')
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','rest_framework','shop']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'shop'/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':dj_database_url.config(default=f'sqlite:///{BASE_DIR}/db.sqlite3',conn_max_age=60)}
AUTH_USER_MODEL='shop.Customer'
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':10}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='en-in'
TIME_ZONE='Asia/Kolkata'
USE_I18N=True
USE_TZ=True
STATIC_URL='/static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
MEDIA_URL='/media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default']={'BACKEND':'storages.backends.s3.S3Storage','OPTIONS':{'bucket_name':os.environ['AWS_STORAGE_BUCKET_NAME'],'region_name':os.getenv('AWS_REGION','ap-south-1'),'custom_domain':os.getenv('MEDIA_CDN_DOMAIN') or None,'querystring_auth':False,'default_acl':None,'object_parameters':{'CacheControl':'max-age=31536000, immutable'}}}
REDIS_URL=os.getenv('REDIS_URL','')
CACHES={'default': {'BACKEND':'django.core.cache.backends.redis.RedisCache','LOCATION':REDIS_URL}} if REDIS_URL else {'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
CELERY_BROKER_URL=REDIS_URL or 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND=CELERY_BROKER_URL
CELERY_BEAT_SCHEDULE={'expire-unpaid-orders':{'task':'shop.tasks.expire_orders','schedule':60.0}}
REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework.authentication.SessionAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.AllowAny'],'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle','rest_framework.throttling.UserRateThrottle'],'DEFAULT_THROTTLE_RATES':{'anon':'180/min','user':'360/min','auth':'10/min'},'EXCEPTION_HANDLER':'shop.api.exception_handler'}
CSRF_TRUSTED_ORIGINS=os.getenv('CSRF_TRUSTED_ORIGINS','http://localhost:3000,http://localhost:8080').split(',')
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
CSRF_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG
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
DATA_UPLOAD_MAX_MEMORY_SIZE=3*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE=3*1024*1024
CASHFREE_APP_ID=os.getenv('CASHFREE_APP_ID','')
CASHFREE_SECRET_KEY=os.getenv('CASHFREE_SECRET_KEY','')
CASHFREE_ENVIRONMENT=os.getenv('CASHFREE_ENVIRONMENT','sandbox')
CASHFREE_API_VERSION=os.getenv('CASHFREE_API_VERSION','2025-01-01')
PUBLIC_SITE_URL=os.getenv('NEXT_PUBLIC_SITE_URL','http://localhost:3000').rstrip('/')
if CASHFREE_ENVIRONMENT not in ['sandbox','production']:
    raise ImproperlyConfigured('CASHFREE_ENVIRONMENT must be sandbox or production')
WHATSAPP_TOKEN=os.getenv('WHATSAPP_TOKEN','')
WHATSAPP_PHONE_ID=os.getenv('WHATSAPP_PHONE_ID','')
WHATSAPP_OTP_TEMPLATE=os.getenv('WHATSAPP_OTP_TEMPLATE','')
WHATSAPP_GRAPH_VERSION=os.getenv('WHATSAPP_GRAPH_VERSION','')
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']=['shop.security.SafeSessionAuthentication']
REST_FRAMEWORK['EXCEPTION_HANDLER']='shop.security.exception_handler'

PASSWORD_RESET_TIMEOUT=3600
EMAIL_TIMEOUT=10
