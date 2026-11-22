from django.urls import path
from . import views

urlpatterns = [
    path('generate-notes/<int:kelas_id>/', views.ai_generate_notes_kelas_view, name='ai_generate_notes_kelas'),
]
