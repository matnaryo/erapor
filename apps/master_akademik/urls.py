from django.urls import path
from . import views

urlpatterns = [
    path('murid/', views.murid_list_view, name='murid_list'),
    path('murid/tambah/', views.murid_create_view, name='murid_create'),
    path('murid/<int:pk>/', views.murid_detail_view, name='murid_detail'),
    path('murid/<int:pk>/edit/', views.murid_update_view, name='murid_update'),
    path('kelas/', views.kelas_list_view, name='kelas_list'),
]
