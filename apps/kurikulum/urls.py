from django.urls import path
from . import views

urlpatterns = [
    path('mupel/', views.mupel_list_view, name='mupel_list'),
    path('kktp/', views.kktp_manage_view, name='kktp_manage'),
    path('tp/', views.tp_list_view, name='tp_list'),
]
