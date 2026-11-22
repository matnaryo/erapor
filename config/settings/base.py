import os
from pathlib import Path
from dotenv import load_dotenv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env', override=True)

SECRET_KEY = os.getenv('SECRET_KEY', 'insecure-key-erapor-lhs-sdit-luqman-al-hakim-sleman-2026')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',')]

# Application definition
UNFOLD_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
]

LOCAL_APPS = [
    'apps.core.apps.CoreConfig',
    'apps.master_akademik.apps.MasterAkademikConfig',
    'apps.kurikulum.apps.KurikulumConfig',
    'apps.penilaian.apps.PenilaianConfig',
    'apps.ai_assistant.apps.AiAssistantConfig',
    'apps.export_import.apps.ExportImportConfig',
    'apps.printing.apps.PrintingConfig',
]

INSTALLED_APPS = UNFOLD_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.global_school_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization (WIB & Indonesia)
LANGUAGE_CODE = 'id-id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Uploads, Kop Sekolah, Foto Murid, Excel)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Local AI Configuration (Ollama on Dell T30)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')
if not OLLAMA_MODEL or 'qwen3' in OLLAMA_MODEL.lower():
    OLLAMA_MODEL = 'qwen2.5:1.5b'

# School Profile Defaults
DEFAULT_KOTA = os.getenv('DEFAULT_KOTA', 'Sleman')
DEFAULT_SEKOLAH_NAMA = os.getenv('DEFAULT_SEKOLAH_NAMA', 'SD Islam Terpadu Luqman Al Hakim Sleman')
DEFAULT_ALAMAT = os.getenv('DEFAULT_ALAMAT', 'Jl. Palagan Tentara Pelajar No. 52 Sedan, Sariharjo, Ngaglik, Sleman, D.I. Yogyakarta 55581')

# Django Unfold Configuration (Modern Tailwind Admin Theme)
UNFOLD = {
    "SITE_TITLE": "e-Rapor eLHaEs Admin",
    "SITE_HEADER": "SDIT Luqman Al Hakim Sleman",
    "SITE_SUBHEADER": "Portal Administrasi Kurikulum Merdeka",
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": lambda request: "/static/img/logo_sdit_lhs.png",
        "dark": lambda request: "/static/img/logo_sdit_lhs.png",
    },
    "SITE_LOGO": {
        "light": lambda request: "/static/img/logo_sdit_lhs.png",
        "dark": lambda request: "/static/img/logo_sdit_lhs.png",
    },
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "oklch(98.5% .014 160)",
            "100": "oklch(96% .035 160)",
            "200": "oklch(91% .075 160)",
            "300": "oklch(84% .125 160)",
            "400": "oklch(74% .175 160)",
            "500": "oklch(60% .210 160)",  # Emerald primary
            "600": "oklch(52% .190 160)",
            "700": "oklch(44% .160 160)",
            "800": "oklch(36% .120 160)",
            "900": "oklch(28% .085 160)",
            "950": "oklch(18% .050 160)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Aplikasi Utama"),
                "separator": True,
                "items": [
                    {
                        "title": _("Kembali ke e-Rapor"),
                        "icon": "arrow_back",
                        "link": reverse_lazy("dashboard"),
                    },
                ],
            },
            {
                "title": _("Master Lembaga"),
                "separator": True,
                "items": [
                    {
                        "title": _("Profil SDIT (Kop & Logo)"),
                        "icon": "domain",
                        "link": reverse_lazy("admin:core_sekolah_changelist"),
                    },
                    {
                        "title": _("Data Pendidik & Tendik"),
                        "icon": "badge",
                        "link": reverse_lazy("admin:core_pendidik_changelist"),
                    },
                    {
                        "title": _("Tahun Ajaran"),
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:master_akademik_tahunajaran_changelist"),
                    },
                    {
                        "title": _("Semester"),
                        "icon": "event_repeat",
                        "link": reverse_lazy("admin:master_akademik_semester_changelist"),
                    },
                ],
            },
            {
                "title": _("Struktur Akademik"),
                "separator": True,
                "items": [
                    {
                        "title": _("Fase Kurikulum"),
                        "icon": "flag",
                        "link": reverse_lazy("admin:master_akademik_fase_changelist"),
                    },
                    {
                        "title": _("Rombel / Kelas"),
                        "icon": "meeting_room",
                        "link": reverse_lazy("admin:master_akademik_kelas_changelist"),
                    },
                ],
            },
            {
                "title": _("Penugasan & Kurikulum"),
                "separator": True,
                "items": [
                    {
                        "title": _("Plotting Guru Pengampu"),
                        "icon": "assignment_ind",
                        "link": reverse_lazy("admin:kurikulum_pembelajarankelas_changelist"),
                    },
                    {
                        "title": _("11 Mata Pelajaran"),
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:kurikulum_matapelajaran_changelist"),
                    },
                ],
            },
            {
                "title": _("Autentikasi & Pengguna"),
                "separator": True,
                "items": [
                    {
                        "title": _("Akun Pengguna"),
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": _("Grup & Hak Akses"),
                        "icon": "security",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}
