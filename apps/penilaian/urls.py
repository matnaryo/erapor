from django.urls import path
from . import views

urlpatterns = [
    path('matriks/', views.nilai_matrix_view, name='nilai_matrix'),
    path('mupel/<int:pembelajaran_id>/', views.nilai_mupel_input_view, name='nilai_mupel_input'),
    path('kokurikuler/<int:kelas_id>/', views.kokurikuler_input_view, name='kokurikuler_input'),
    path('ekskul-prestasi/<int:anggota_id>/', views.ekskul_prestasi_input_view, name='ekskul_prestasi_input'),
    path('absen/<int:kelas_id>/', views.rekap_absen_input_view, name='rekap_absen_input'),
    path('catatan-wali/<int:kelas_id>/', views.catatan_wali_input_view, name='catatan_wali_input'),
]
