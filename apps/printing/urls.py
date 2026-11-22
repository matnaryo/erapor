from django.urls import path
from . import views

urlpatterns = [
    path('', views.class_print_list_view, name='class_print_default'),
    path('kelas/<int:kelas_id>/', views.class_print_list_view, name='class_print_list'),
    path('rapor/<int:anggota_id>/', views.rapor_print_view, name='rapor_print'),
    path('kover/<int:anggota_id>/', views.cover_print_view, name='cover_print'),
]
