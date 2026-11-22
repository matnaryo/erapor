from django.contrib import admin
from .models import Sekolah, Pendidik

@admin.register(Sekolah)
class SekolahAdmin(admin.ModelAdmin):
    list_display = ('nama', 'npsn', 'nss', 'kabupaten_kota', 'kepala_sekolah_nama')

@admin.register(Pendidik)
class PendidikAdmin(admin.ModelAdmin):
    list_display = ('nama_lengkap', 'role', 'nip', 'niy', 'no_hp', 'is_active')
    list_filter = ('role', 'is_active', 'jenis_kelamin')
    search_fields = ('nama_lengkap', 'nip', 'niy')
