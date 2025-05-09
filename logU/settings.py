"""
Django settings for logU project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
DOMAIN='127.0.0.1:8000'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-9%jr3gvaliclxghocx!3plwtt#_6wf=x%=#sm4gntyb(sdrt8x')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Determine if running on Render
ON_RENDER = os.environ.get('RENDER', False)

# Flag to enable/disable ML features
ENABLE_ML_FEATURES = not ON_RENDER  # Disable ML in production on Render

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,hosting-kq0v.onrender.com,.onrender.com').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'home',
    'django_apscheduler',

    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'whitenoise.runserver_nostatic',
    'whitenoise',
       
]
AUTH_USER_MODEL = 'home.Users'

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

if not ON_RENDER:
    # Only use sites middleware in development
    MIDDLEWARE.append('django.contrib.sites.middleware.CurrentSiteMiddleware')

ROOT_URLCONF = 'logU.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
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

WSGI_APPLICATION = 'logU.wsgi.application'


LOGIN_URL='login'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# For Render deployment, use PostgreSQL if available, otherwise use SQLite
# Note that SQLite on Render is ephemeral and will be reset between deployments
if ON_RENDER:
    # Use SQLite but in a persistent directory
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join('/data', 'db.sqlite3'),  # Render persistent disk
        }
    }
else:
    # Local development database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  

# Use a simpler storage backend on Render to avoid manifest issues
if ON_RENDER:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    
# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com' 
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'amaltomy321@gmail.com'
EMAIL_HOST_PASSWORD='mqhi mmoe ucqk dzjj'
DEFAULT_FROM_EMAIL = 'amaltomy321@gmail.com'

# Django sites framework setting
SITE_ID = 1

# django-allauth settings
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Disable email verification since we're not using the sites framework in production

TWILIO_ACCOUNT_SID = 'ACa7a2f6611c41f82d39f3cdcc9fc0a2fb'
TWILIO_AUTH_TOKEN = '1d5c259c581172b354336a893ea3e8eb'
TWILIO_PHONE_NUMBER = '+12089032893'

# Add this to your existing settings

OPENWEATHERMAP_API_KEY = '45b01a7f6a9893cc9370a6fd91f105fb'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = '/welcome'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': '154954218357-uko4l2e703urciu6801batsh8g0gqfna.apps.googleusercontent.com',
            'secret': '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',
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'prompt': 'select_account',
            'access_type': 'online',
        },
        'LOGIN_REDIRECT_URL': 'welcome.html',  # Redirect URL after Google login
        'OAUTH2_REDIRECT_URI': 'http://localhost:8000/accounts/google/login/callback/',
    }
}


# Additional settings for email verification and sign up
ACCOUNT_EMAIL_REQUIRED = True
# Use 'none' in production to avoid dependency on sites framework
ACCOUNT_EMAIL_VERIFICATION = 'none' if ON_RENDER else 'mandatory'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
SOCIALACCOUNT_LOGIN_ON_GET=True


STRIPE_PUBLIC_KEY = 'pk_test_51OCkghSBuIxwYSiTmCNMdgc0IMrgQHhcAvocnizZpjj6MPVFZ4mYldxbWTAbEFcHN24niT2eQ3ZDMs77Uk5vcVpr00fEoozoND'
STRIPE_SECRET_KEY = 'sk_test_51OCkghSBuIxwYSiTZeJkEXw2z2OjBvFdQQtmebhs1oIyw1Y3JIqtCQwit6fbirruGnlfnJyGxV17DivYqtK4LyI1000VP3scQg'

# Cache settings - use in-memory cache to save resources
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 1 day in seconds

# Optimize database connections
CONN_MAX_AGE = 600  # 10 minutes

# Disable unused apps in production
if not DEBUG:
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in [
        # List any apps you want to disable in production
    ]]

# Logging configuration to reduce memory usage
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
