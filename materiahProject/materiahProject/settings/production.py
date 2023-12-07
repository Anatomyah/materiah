from .base import *

DEBUG = False
ALLOWED_HOSTS = ['172.31.27.63', 'ec2-172-31-27-63.eu-central-1.compute.amazonaws.com']

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://172.31.27.63",
    "http://ec2-172-31-27-63.eu-central-1.compute.amazonaws.com",
]

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'materiah',
        'USER': os.environ.get('DB_USERNAME'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': 'materiah.cgyfysgmccyk.eu-central-1.rds.amazonaws.com',
        'PORT': '5432',
    }
}

# Caches

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
