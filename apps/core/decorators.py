from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def get_pendidik_profile(user):
    """Mengambil profil pendidik dari user yang sedang login."""
    if not user.is_authenticated:
        return None
    return getattr(user, 'profil_pendidik', None)

def is_superadmin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profil = get_pendidik_profile(user)
    return profil and profil.role == 'SUPERADMIN'

def is_kepala_sekolah(user):
    profil = get_pendidik_profile(user)
    return is_superadmin(user) or (profil and profil.role == 'KEPALA_SEKOLAH')

def is_kurikulum(user):
    profil = get_pendidik_profile(user)
    return is_superadmin(user) or (profil and profil.role == 'KURIKULUM')

def is_wali_kelas(user):
    profil = get_pendidik_profile(user)
    return is_superadmin(user) or (profil and profil.role == 'WALI_KELAS')

def is_guru_mapel(user):
    profil = get_pendidik_profile(user)
    return is_superadmin(user) or (profil and profil.role in ['GURU_MAPEL', 'WALI_KELAS'])

def role_required(allowed_roles):
    """
    Decorator untuk membatasi akses view berdasarkan peran RBAC Pendidik.
    allowed_roles: list dari ['SUPERADMIN', 'KEPALA_SEKOLAH', 'KURIKULUM', 'WALI_KELAS', 'GURU_MAPEL', 'PEMBINA_EKSKUL']
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Silakan login terlebih dahulu untuk mengakses halaman ini.")
                return redirect('login')
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profil = get_pendidik_profile(request.user)
            if not profil or not profil.is_active:
                messages.error(request, "Akun Pendidik Anda belum aktif atau tidak terdaftar.")
                return redirect('login')

            if profil.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "Anda tidak memiliki wewenang untuk mengakses halaman tersebut.")
            return redirect('dashboard')
        return _wrapped_view
    return decorator
