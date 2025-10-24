from pathlib import Path
import os
from decouple import config  # لإحضار القيم من ملف .env

# ----- Paths -----
BASE_DIR = Path(__file__).resolve().parent.parent

# ----- Security -----
SECRET_KEY = 'django-insecure-9_$az03iqojjq#l_f7=^penpwyz6=qipvz$2m%mou$1yq%wao3'
DEBUG = True
ALLOWED_HOSTS = ['prima-dd2g.onrender.com', 'localhost', '127.0.0.1', '192.168.10.166']

# ----- Installed Apps -----
INSTALLED_APPS = [
    'myapp',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'crispy_forms',
    'crispy_bootstrap5',
]

CRISPY_TEMPLATE_PACK = 'bootstrap5'
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'

# ----- Middleware -----
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # لدعم اللغات
]

# ----- URLs & Templates -----
ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'myapp' / 'templates' / 'myapp'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'myapp.context_processors.user_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'

# ----- Database (PostgreSQL) -----
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='prima_8l72'),
        'USER': config('DB_USER', default='prima_8l72_user'),
        'PASSWORD': config('DB_PASSWORD', default='DiE0oU4dflYwmVM7Kp5EKTOXvkQQjZD6'),
        'HOST': config('DB_HOST', default='dpg-d3tjb0f5r7bs73esddq0-a.oregon-postgres.render.com'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# ----- Password Validators -----
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# ----- Localization -----
LANGUAGE_CODE = 'ar'

LANGUAGES = [
    ('ar', 'العربية'),
    ('he', 'עברית'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

TIME_ZONE = 'Asia/Amman'
USE_I18N = True
USE_TZ = True

# ----- Static Files -----
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'myapp/static')]

# ----- Authentication -----
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ----- Email -----
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'abuzain186@gmail.com'
EMAIL_HOST_PASSWORD = 'xbtd bqnh rstb adzq'  # ضع كلمة المرور هنا
DEFAULT_FROM_EMAIL = 'webmaster@yourdomain.com'
