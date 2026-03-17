from .base import *
from decouple import config

DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ['35.237.160.207','cooltimedia.com','https://cooltimedia.com/','http://cooltimedia.com/']

CSRF_TRUSTED_ORIGINS = [
    'https://www.cooltimedia.com',
    'https://cooltimedia.com',
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
# STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
