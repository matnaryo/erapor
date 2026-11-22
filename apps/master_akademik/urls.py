from django.urls import path
from . import views

urlpatterns = [
    path('murid/', views.murid_list_view, name='murid_list'),
    path('murid/tambah/', views.murid_create_view, name='murid_create'),
    path('murid/<int:pk>/', views.murid_detail_view, name='murid_detail'),
    path('murid/<int:pk>/edit/', views.murid_update_view, name='murid_update'),
    path('murid/<int:pk>/tempatkan-kelas/', views.murid_tempatkan_kelas_view, name='murid_tempatkan_kelas'),
    path('kelas/', views.kelas_list_view, name='kelas_list'),
    path('kelas/<int:pk>/anggota/', views.kelas_anggota_view, name='kelas_anggota'),
    path('kelas/<int:kelas_id>/hapus-anggota/<int:anggota_id>/', views.kelas_hapus_anggota_view, name='kelas_hapus_anggota'),
]
