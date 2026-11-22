from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import TahunAjaran, Semester, Fase, Kelas

# Murid dan AnggotaKelas (Plotting Rombel) dikelola sepenuhnya melalui antarmuka
# Buku Induk Murid dan Kelola Anggota Kelas di aplikasi e-Rapor, sehingga tidak
# dimunculkan di Django Admin Portal agar tampilan admin tetap simpel dan terfokus.

@admin.register(TahunAjaran)
class TahunAjaranAdmin(ModelAdmin):
    list_display = ('nama', 'tanggal_mulai', 'tanggal_selesai', 'is_active')
    list_filter = ('is_active',)

@admin.register(Semester)
class SemesterAdmin(ModelAdmin):
    list_display = ('tahun_ajaran', 'semester', 'titimangsa_tanggal', 'titimangsa_tempat', 'is_active')
    list_filter = ('semester', 'is_active')

@admin.register(Fase)
class FaseAdmin(ModelAdmin):
    list_display = ('kode', 'nama')

@admin.register(Kelas)
class KelasAdmin(ModelAdmin):
    list_display = ('nama', 'tingkat', 'fase', 'tahun_ajaran', 'wali_kelas')
    list_filter = ('tingkat', 'fase', 'tahun_ajaran')
    search_fields = ('nama',)
