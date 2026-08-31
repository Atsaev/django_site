import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'atsaev-dev.ru']
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    'django_ckeditor_5',
    'imagekit',

    'blog',
    'portfolio',
    'resume',
]

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]
    INTERNAL_IPS = ['127.0.0.1']

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
LANGUAGE_CODE = "ru"

TIME_ZONE = "Europe/Moscow"

SITE_ID = 1

USE_I18N = True

USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Загрузки (поля моделей) и медиа CKEditor идут через хранилище,
# транслитерирующее кириллические имена файлов.
DEFAULT_FILE_STORAGE = 'config.storage.MediaFileSystemStorage'

STORAGES = {
    "default": {
        "BACKEND": DEFAULT_FILE_STORAGE,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# в тестах нет собранного манифеста — используем простое хранилище
if "test" in sys.argv:
    STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading", "|",
            "bold", "italic", "underline", "strikethrough", "subscript", "superscript", "removeFormat", "|",
            "fontSize", "fontColor", "fontBackgroundColor", "highlight", "|",
            "alignment", "|",
            "bulletedList", "numberedList", "todoList", "|",
            "outdent", "indent", "|",
            "link", "blockQuote", "insertTable", "|",
            "uploadImage", "mediaEmbed", "|",
            "codeBlock", "horizontalLine", "specialCharacters", "|",
            "findAndReplace", "sourceEditing", "|",
            "undo", "redo",
        ],
        "codeBlock": {
            "languages": [
                {"language": "python", "label": "Python"},
                {"language": "bash", "label": "Bash"},
                {"language": "javascript", "label": "JavaScript"},
                {"language": "json", "label": "JSON"},
                {"language": "sql", "label": "SQL"},
                {"language": "yaml", "label": "YAML"},
                {"language": "dockerfile", "label": "Dockerfile"},
            ],
        },
        "image": {
            "toolbar": [
                "imageTextAlternative", "linkImage", "|",
                "imageStyle:alignLeft", "imageStyle:alignCenter", "imageStyle:alignRight", "|",
                "resizeImage",
            ],
            "resizeOptions": [
                {"name": "resizeImage:25", "value": "25", "label": "25%"},
                {"name": "resizeImage:50", "value": "50", "label": "50%"},
                {"name": "resizeImage:75", "value": "75", "label": "75%"},
            ],
        },
        "table": {
            "contentToolbar": ["tableColumn", "tableRow", "mergeTableCells", "tableProperties", "tableCellProperties"],
        },
        "height": 500,
    },
}
CKEDITOR_5_FILE_STORAGE = 'config.storage.MediaFileSystemStorage'

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = ["https://atsaev-dev.ru"]
