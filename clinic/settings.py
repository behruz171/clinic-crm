import os
from pathlib import Path
from datetime import timedelta
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-(5h7k9hkid4bbrbm6$-f!2v^9mu$xc-t=dzq5da6$$2c%)p!54'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'jazzmin',  # jazzmin eng tepada bo'lishi kerak
    'daphne',
    'channels',
    'chartjs',  # django-admin-charts o'rniga
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    'corsheaders',
    'app',
    'app2'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'clinic.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'clinic.wsgi.application'

ASGI_APPLICATION = 'clinic.asgi.application'  # Replace clinic_crm with your project name

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_VERSION': 'v1',
    'DEFAULT_ROUTER': 'api',
    'DEFAULT_PAGINATION_CLASS': 'app.pagination.CustomPagination',  # Use the custom pagination class
    'PAGE_SIZE': 10,
}

CORS_ALLOWED_ORIGINS = [
    "https://clinic-crm-alpha.vercel.app",
    "https://cliniccrm.pythonanywhere.com",  # Frontend domeni
    "http://localhost:3001",  # Agar frontend localhostda ishlayotgan bo'lsa
    "http://localhost:3000"
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

SIMPLE_JWT = {
#     # ✅ ACCESS TOKEN yashash muddati (foydalanuvchi API'ga kirishda ishlatadi)
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),  # 30 daqiqa yashaydi
    
#     # ✅ REFRESH TOKEN yashash muddati (access token yangilash uchun)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # 7 kun yashaydi
    
#     # ✅ ID TOKEN (agar ishlatilsa) yashash muddati
#     'ID_TOKEN_LIFETIME': timedelta(minutes=5),  # 5 daqiqa yashaydi

#     # ✅ Yangi ACCESS TOKEN yaratish uchun REFRESH TOKEN ishlatiladimi?
#     'ROTATE_REFRESH_TOKENS': False,  # Agar True bo‘lsa, har safar refresh qilganda yangi refresh token ham beriladi
    
#     # ✅ REFRESH TOKEN eski versiyasini yo‘q qilish
#     'BLACKLIST_AFTER_ROTATION': False,  # Agar True bo‘lsa, eski refresh token yaroqsiz bo‘ladi

#     # ✅ JWT SIGNATURE ALGORITHM
#     'ALGORITHM': 'HS256',  # HMAC SHA256 algoritmidan foydalaniladi (standart)

#     # ✅ SECRET KEY (o‘zgarishsiz qoldirish mumkin, `SECRET_KEY` dan foydalanadi)
#     'SIGNING_KEY': None,  

#     # ✅ PUBLIC/PRIVATE KEY (RSA yoki EC algoritmlar uchun ishlatiladi)
#     'VERIFYING_KEY': None,
#     'AUDIENCE': None,
#     'ISSUER': None,

#     # ✅ TOKEN YUBORILISH USULI
#     'AUTH_HEADER_TYPES': ('Bearer',),  # `Authorization: Bearer <token>` usuli
#     'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',  # Header nomi
    
#     # ✅ USER IDENTIFIKATORI
#     'USER_ID_FIELD': 'id',  # Foydalanuvchini aniqlash uchun qaysi maydon ishlatiladi (odatiy: `id`)
#     'USER_ID_CLAIM': 'user_id',  # Token ichida qaysi kalit bilan user ID saqlanadi

#     # ✅ AUTHORIZATION HEADER KELMASA, COOKIE`DA TEKSHIRISH
#     'AUTH_COOKIE': None,  # Agar JWT cookie orqali ishlatilsa, shu yerdan tekshiriladi
#     'AUTH_COOKIE_DOMAIN': None,
#     'AUTH_COOKIE_SECURE': False,  # HTTPS talab qilinishi kerakmi?
#     'AUTH_COOKIE_HTTP_ONLY': True,  # Faqat HTTP orqali yuborilsin
#     'AUTH_COOKIE_PATH': '/',
#     'AUTH_COOKIE_SAMESITE': 'Lax',

#     # ✅ SLIDING TOKEN UCHUN SOZLAMALAR (standart refresh token o‘rniga ishlatiladi)
#     'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
#     'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}
# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = 'staticfiles/'

MEDIA_URL = '/media/'  # Media fayllarga URL orqali kirish uchun
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Media fayllarni saqlash uchun katalog

# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static'),
# ]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'app.User'

# Jazzmin sozlamalari
JAZZMIN_SETTINGS = {
    # Asosiy
    "site_title": "Clinic CRM",
    "site_header": "Clinic CRM",
    "site_brand": "CRM",
    "welcome_sign": "Tizimga xush kelibsiz",
    "copyright": "Clinic CRM",
    
    # Qidiruv
    "search_model": ["app.User", "app.Clinic"],
    "user_avatar": None,
    
    # Navigation
    "show_sidebar": True,
    "navigation_expanded": False,
    
    # Menu tartibi
    "order_with_respect_to": [
        "app.Clinic",
        "app.User",
        "auth",
    ],
    
    # Ikonkalar
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "app.User": "fas fa-user-md",
        "app.Clinic": "fas fa-hospital",
        "app.Statistics": "fas fa-chart-bar",
        "app.Notification": "fas fa-bell",
        "app.ClinicNotification": "fas fa-envelope",
        "app.Cabinet": "fa-solid fa-hospital-user",
        "app.Customer": "fa-solid fa-user-injured",
        "app.Meeting": "fa-solid fa-calendar-check",
        "app.Branch": "fa-solid fa-building",
        "app.UserNotification": "fa-solid fa-inbox",
        "app.Room": "fa-solid fa-bed",
        "app.CashWithdrawal": "fa-solid fa-credit-card",
        "app.Task": "fa-solid fa-list-check",
        "app.RoomHistory": "fa-solid fa-clock-rotate-left",
        "app2.Medicine": "fa-solid fa-pills",
        "app2.MedicineHistory": "fa-solid fa-clock-rotate-left",
        "app2.MedicineSchedule": "fa-solid fa-clipboard-list",
        "app2.VitalSign": "fa-solid fa-heart-pulse",
    },
    
    # Custom linklar
    # "custom_links": {
    #     "app": [{
    #         "name": "Statistika", 
    #         "url": "admin:app_statistics_changelist", 
    #         "icon": "fas fa-chart-line"
    #     }]
    # },
}

# UI sozlamalari o'zgarmaydi
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-teal",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "cosmo",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'api_key': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    },
}

# Email sozlamalari
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'starclaudsuport@gmail.com'  # Gmail pochtangiz
EMAIL_HOST_PASSWORD = 'yhvqsewlnwwqvsco'  # Gmail app password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
