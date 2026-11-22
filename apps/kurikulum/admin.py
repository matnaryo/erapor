from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import MataPelajaran, KKTPRentang, TujuanPembelajaran, PembelajaranKelas

class KKTPRentangInline(TabularInline):
    model = KKTPRentang
    extra = 0

@admin.register(MataPelajaran)
class MataPelajaranAdmin(ModelAdmin):
    list_display = ('urutan', 'kode', 'nama', 'kategori', 'is_active')
    list_filter = ('kategori', 'is_active')
    search_fields = ('nama', 'kode')
    ordering = ('urutan',)
    inlines = [KKTPRentangInline]

@admin.register(KKTPRentang)
class KKTPRentangAdmin(ModelAdmin):
    list_display = ('mata_pelajaran', 'fase', 'predikat', 'label', 'nilai_min', 'nilai_max')
    list_filter = ('fase', 'predikat', 'mata_pelajaran')
    search_fields = ('mata_pelajaran__nama',)

@admin.register(TujuanPembelajaran)
class TujuanPembelajaranAdmin(ModelAdmin):
    list_display = ('kode', 'mata_pelajaran', 'fase', 'tingkat', 'semester', 'urutan')
    list_filter = ('tingkat', 'semester', 'fase', 'mata_pelajaran')
    search_fields = ('kode', 'deskripsi')

@admin.register(PembelajaranKelas)
class PembelajaranKelasAdmin(ModelAdmin):
    list_display = ('kelas', 'mata_pelajaran', 'guru_pengampu', 'semester')
    list_filter = ('kelas', 'mata_pelajaran', 'semester')
    search_fields = ('guru_pengampu__nama_lengkap', 'mata_pelajaran__nama')
