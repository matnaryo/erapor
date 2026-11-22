from django.contrib import admin
from .models import (
    NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai,
    PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
)

@admin.register(NilaiAkhir)
class NilaiAkhirAdmin(admin.ModelAdmin):
    list_display = ('anggota_kelas', 'pembelajaran_kelas', 'nilai_angka', 'predikat')
    list_filter = ('pembelajaran_kelas__mata_pelajaran', 'pembelajaran_kelas__kelas')
    search_fields = ('anggota_kelas__murid__nama_lengkap',)

@admin.register(KokurikulerNilai)
class KokurikulerNilaiAdmin(admin.ModelAdmin):
    list_display = ('anggota_kelas', 'semester', 'aspek', 'predikat')
    list_filter = ('semester', 'predikat')
    search_fields = ('anggota_kelas__murid__nama_lengkap',)

@admin.register(EkstrakurikulerNilai)
class EkstrakurikulerNilaiAdmin(admin.ModelAdmin):
    list_display = ('urutan', 'kegiatan', 'predikat', 'anggota_kelas', 'semester')
    list_filter = ('semester', 'kegiatan')
    search_fields = ('anggota_kelas__murid__nama_lengkap', 'kegiatan')
    ordering = ('urutan',)

@admin.register(PrestasiMurid)
class PrestasiMuridAdmin(admin.ModelAdmin):
    list_display = ('urutan', 'jenis_prestasi', 'anggota_kelas', 'semester')
    list_filter = ('semester',)
    search_fields = ('anggota_kelas__murid__nama_lengkap', 'jenis_prestasi')
    ordering = ('urutan',)

@admin.register(Ketidakhadiran)
class KetidakhadiranAdmin(admin.ModelAdmin):
    list_display = ('anggota_kelas', 'semester', 'sakit', 'izin', 'tanpa_keterangan')
    list_filter = ('semester',)
    search_fields = ('anggota_kelas__murid__nama_lengkap',)

@admin.register(CatatanWaliKelas)
class CatatanWaliKelasAdmin(admin.ModelAdmin):
    list_display = ('anggota_kelas', 'semester', 'is_generated_by_ai', 'updated_at')
    list_filter = ('is_generated_by_ai', 'semester')
    search_fields = ('anggota_kelas__murid__nama_lengkap', 'catatan')
