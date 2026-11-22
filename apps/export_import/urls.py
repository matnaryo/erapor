from django.urls import path
from . import views

urlpatterns = [
    path('', views.export_import_center_view, name='export_import_center'),
    path('template/<int:pembelajaran_id>/', views.download_template_view, name='download_template'),
    path('import/<int:pembelajaran_id>/', views.import_nilai_view, name='import_nilai'),
    path('leger/<int:kelas_id>/', views.download_leger_view, name='download_leger'),
]
