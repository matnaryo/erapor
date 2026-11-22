from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import Sekolah, Pendidik

admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

@admin.register(Sekolah)
class SekolahAdmin(ModelAdmin):
    list_display = ('nama', 'npsn', 'nss', 'kabupaten_kota', 'kepala_sekolah_nama')
    search_fields = ('nama', 'npsn', 'kepala_sekolah_nama')

@admin.register(Pendidik)
class PendidikAdmin(ModelAdmin):
    list_display = ('nama_lengkap', 'role', 'nip', 'niy', 'no_hp', 'is_active')
    list_filter = ('role', 'is_active', 'jenis_kelamin')
    search_fields = ('nama_lengkap', 'nip', 'niy')
