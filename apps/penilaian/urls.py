from django.urls import path
from . import views

urlpatterns = [
    path('matriks/', views.nilai_matrix_view, name='nilai_matrix'),
    path('mupel/<int:pembelajaran_id>/', views.nilai_mupel_input_view, name='nilai_mupel_input'),
    path('api/generate-capaian-ai/', views.api_generate_capaian_ai_view, name='api_generate_capaian_ai'),
    
    # Kokurikuler
    path('kokurikuler/matriks/', views.kokurikuler_matrix_view, name='kokurikuler_matrix'),
    path('kokurikuler/matriks/<int:kelas_id>/', views.kokurikuler_matrix_view, name='kokurikuler_matrix_kelas'),
    path('kokurikuler/penilaian/', views.kokurikuler_input_view, name='kokurikuler_input_default'),
    path('kokurikuler/<int:kelas_id>/', views.kokurikuler_input_view, name='kokurikuler_input'),

    # Ekstrakurikuler (Matriks 6 Kelompok Kolom)
    path('ekskul-matriks/', views.ekskul_matrix_view, name='ekskul_matrix'),
    path('ekskul-matriks/<int:kelas_id>/', views.ekskul_matrix_view, name='ekskul_matrix_kelas'),

    # Prestasi Murid (Matriks 6 Kelompok Kolom)
    path('prestasi-matriks/', views.prestasi_matrix_view, name='prestasi_matrix'),
    path('prestasi-matriks/<int:kelas_id>/', views.prestasi_matrix_view, name='prestasi_matrix_kelas'),

    # Individual / Detail Input
    path('ekskul-prestasi/kelas/<int:kelas_id>/', views.ekskul_prestasi_kelas_view, name='ekskul_prestasi_kelas'),
    path('ekskul-prestasi/<int:anggota_id>/', views.ekskul_prestasi_input_view, name='ekskul_prestasi_input'),
    path('absen/<int:kelas_id>/', views.rekap_absen_input_view, name='rekap_absen_input'),
    path('catatan-wali/<int:kelas_id>/', views.catatan_wali_input_view, name='catatan_wali_input'),
]
