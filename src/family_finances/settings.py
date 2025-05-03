import os
from datetime import timedelta
from pathlib import Path

import sentry_sdk
from django.urls import reverse_lazy
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'p&l%385148kslhtyn^##a1)ilz@4zqj=rq&agdol^##zgl9(vs'
)
ACCESS_TOKEN = os.getenv(
    'ACCESS_TOKEN'
)

DEBUG = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS', '127.0.0.1,localhost'
).split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework.authtoken',
    'djoser',
    'drf_yasg',
    'django_filters',
    'django_extensions',
    'django_bootstrap5',
    'users',
    'transactions',
    'api',
    'export'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'family_finances.urls'

TEMPLATES_DIR = BASE_DIR / 'templates'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
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

WSGI_APPLICATION = 'family_finances.wsgi.application'


USE_SQLITE = os.getenv('USE_SQLITE', 'False').lower() == 'true'

POSTGRESQL_SETTINGS = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'family_finances_2'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', 5432)
    }
}

SQLITE_SETTINGS = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DATABASES = SQLITE_SETTINGS if USE_SQLITE else POSTGRESQL_SETTINGS


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


LANGUAGE_CODE = 'ru-RU'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'collected_static'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication'
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SHELL_PLUS = "ipython"

LOGIN_REDIRECT_URL = reverse_lazy('transactions:home')
LOGOUT_REDIRECT_URL = reverse_lazy('transactions:home')

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'

NOT_ALLOWED_USERNAMES = (
    'admin',
    'superuser',
    'guest',
    'me'
)

CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS', 'http://localhost'
).split(',')


CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройки экспорта в excel
# Для транзакций
TRANSACTIONS_EXPORT_EXCEL_FILENAME = 'transactions.xlsx'
TRANSACTIONS_EXPORT_EXCEL_SHEET_NAME = 'Транзакции'
COL_WIDTH_DATE = 11
COL_WIDTH_TYPE_TRANSACTION = 9
COL_WIDTH_GROUP = 20
COL_WIDTH_VALUE_TRANSACTION = 10
COL_WIDTH_DESCRIPTION = 40
COL_WIDTH_AUTHOR = 15

# Настройки Sentry
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(SENTRY_DSN)
