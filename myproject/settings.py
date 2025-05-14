from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-9_$az03iqojjq#l_f7=^penpwyz6=qipvz$2m%mou$1yq%wao3'
DEBUG = True
ALLOWED_HOSTS = ['prima-dd2g.onrender.com', 'localhost', '127.0.0.1','192.168.10.166']

INSTALLED_APPS = [
    'myapp' ,
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



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # **[تم الإضافة] مهم جدًا لدعم اللغات**
]

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
                'myapp.context_processors.user_notifications',  # <--- تم الإضافة هنا
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ar'  # **[موجود] اللغة الافتراضية للمشروع**

LANGUAGES = [  # **[تم الإضافة] قائمة اللغات اللي هتدعمها**
    ('ar', 'العربية'),
    ('he', 'עברית'),
    ('en', 'English'),
]

LOCALE_PATHS = [  # **[تم الإضافة] مسار فولدر ملفات الترجمة**
    os.path.join(BASE_DIR, 'locale'),
]

TIME_ZONE = 'Asia/Amman'
USE_I18N = True  # **[موجود] تفعيل نظام الترجمة في Django**
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # تم إضافة هذا السطر
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'myapp/static'),
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# إعدادات البريد الإلكتروني (أضف هذه الأسطر في نهاية الملف)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False

EMAIL_HOST_USER = 'abuzain186@gmail.com'
EMAIL_HOST_PASSWORD = 'xbtd bqnh rstb adzq'  # **ضع كلمة المرور هنا!**

DEFAULT_FROM_EMAIL = 'webmaster@yourdomain.com' # ممكن تغير ده لو حابب
