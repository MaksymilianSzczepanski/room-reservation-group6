"""One Django runtime per service; every process loads only its own domain app."""
import os
import sys
from pathlib import Path

SERVICE_NAME = os.environ.get("SERVICE_NAME", "rooms")
SERVICES = {"users", "rooms", "guardians", "reservations", "decisions", "notifications", "search", "reports", "portal"}
if SERVICE_NAME not in SERVICES:
    raise RuntimeError(f"Unknown SERVICE_NAME: {SERVICE_NAME}")

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "local-development-only-change-me")
DEBUG = os.environ.get("DEBUG", "0").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")
INSTALLED_APPS = ["django.contrib.contenttypes"]
if SERVICE_NAME == "users":
    INSTALLED_APPS.append("django.contrib.auth")
if SERVICE_NAME == "portal":
    INSTALLED_APPS.append("django.contrib.staticfiles")
INSTALLED_APPS.append(f"microservices.{SERVICE_NAME}")
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "microservices.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}]
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Europe/Warsaw"
LANGUAGE_CODE = "pl"

if os.environ.get("MICROSERVICES_SQLITE") == "1" or ("test" in sys.argv and os.environ.get("USE_SQLITE_FOR_TESTS", "1") == "1"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "room_reservations"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASS", ""),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {"options": f"-c search_path={SERVICE_NAME}"},
    }}

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "5"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "0") == "1"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "rezerwacje@example.local")
