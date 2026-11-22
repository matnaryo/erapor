from .base import *

DEBUG = True

# Database Configuration
# Defaults to SQLite for local development and tests, switchable to PostgreSQL via .env
USE_POSTGRES = os.getenv('USE_POSTGRES', 'False') == 'True'

if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'erapor_lhs_db'),
            'USER': os.getenv('DB_USER', 'erapor_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'erapor_password'),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
