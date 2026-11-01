DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
SECRET_KEY = "r4dy"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "datatables_listview",
    "datatables_listview.tests",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {},
    },
]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
