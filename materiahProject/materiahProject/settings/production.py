from .base import *

DEBUG = False
ALLOWED_HOSTS = ['3.70.176.24', 'ec2-3-70-176-24.eu-central-1.compute.amazonaws.com']

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
