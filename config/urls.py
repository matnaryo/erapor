"""
URL configuration for e-Rapor eLHaEs project.
SDIT Luqman Al Hakim Sleman
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('akademik/', include('apps.master_akademik.urls')),
    path('kurikulum/', include('apps.kurikulum.urls')),
    path('penilaian/', include('apps.penilaian.urls')),
    path('ai-asisten/', include('apps.ai_assistant.urls')),
    path('cetak/', include('apps.printing.urls')),
    path('excel/', include('apps.export_import.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
