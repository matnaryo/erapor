from django.contrib import admin
from .models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas

@admin.register(TahunAjaran)
class TahunAjaranAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tanggal_mulai', 'tanggal_selesai', 'is_active')
    list_filter = ('is_active',)

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('tahun_ajaran', 'semester', 'titimangsa_tanggal', 'titimangsa_tempat', 'is_active')
    list_filter = ('semester', 'is_active')

@admin.register(Fase)
class FaseAdmin(admin.ModelAdmin):
    list_display = ('kode', 'nama')

@admin.register(Kelas)
class KelasAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tingkat', 'fase', 'tahun_ajaran', 'wali_kelas')
    list_filter = ('tingkat', 'fase', 'tahun_ajaran')
    search_fields = ('nama',)

@admin.register(Murid)
class MuridAdmin(admin.ModelAdmin):
    list_display = ('nisn', 'nis', 'nama_lengkap', 'jenis_kelamin', 'tempat_lahir', 'tanggal_lahir', 'is_active')
    list_filter = ('jenis_kelamin', 'is_active')
    search_fields = ('nama_lengkap', 'nisn', 'nis')

@admin.register(AnggotaKelas)
class AnggotaKelasAdmin(admin.ModelAdmin):
    list_display = ('nomor_absen', 'murid', 'kelas')
    list_filter = ('kelas__tahun_ajaran', 'kelas')
    search_fields = ('murid__nama_lengkap', 'murid__nisn')
