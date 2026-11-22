from .models import Sekolah, Pendidik
from apps.master_akademik.models import TahunAjaran, Semester, Kelas

def global_school_context(request):
    """
    Context processor global untuk seluruh template:
    Profil sekolah, tahun ajaran aktif, semester aktif, dan profil pendidik.
    Mendukung penuh akun Superadmin agar tidak pernah kehilangan hak akses.
    """
    sekolah = Sekolah.objects.first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    sem_aktif = Semester.objects.filter(is_active=True).first()

    pendidik = None
    role = None
    kelas_wali = []

    if request.user.is_authenticated:
        pendidik = getattr(request.user, 'profil_pendidik', None)
        if request.user.is_superuser:
            if not pendidik:
                pendidik, _ = Pendidik.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'nama_lengkap': request.user.get_full_name() or f"Administrator ({request.user.username})",
                        'role': 'SUPERADMIN',
                        'is_active': True,
                    }
                )
            role = 'SUPERADMIN'
            # Superadmin memiliki akses ke seluruh rombel kelas aktif
            kelas_wali = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
        elif pendidik:
            role = pendidik.role
            if pendidik.role == 'WALI_KELAS':
                kelas_wali = pendidik.kelas_asuhan.all()

    return {
        'sekolah_aktif': sekolah,
        'tahun_ajaran_aktif': ta_aktif,
        'semester_aktif': sem_aktif,
        'profil_pendidik': pendidik,
        'user_role': role,
        'kelas_wali_list': kelas_wali,
    }
