from .models import Sekolah, Pendidik
from apps.master_akademik.models import TahunAjaran, Semester, Kelas

def global_school_context(request):
    """
    Context processor global untuk seluruh template:
    Profil sekolah, tahun ajaran aktif, semester aktif, profil pendidik, dan default kelas.
    Mengutamakan profil peran Pendidik terdaftar (Wali Kelas, Guru Mapel, Superadmin).
    """
    sekolah = Sekolah.objects.first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    sem_aktif = Semester.objects.filter(is_active=True).first()

    pendidik = None
    role = None
    kelas_wali = []
    default_kelas = None

    if request.user.is_authenticated:
        pendidik = getattr(request.user, 'profil_pendidik', None)

        if pendidik:
            role = pendidik.role
            if pendidik.role == 'WALI_KELAS':
                kelas_wali = pendidik.kelas_asuhan.all()
                default_kelas = kelas_wali.first() if hasattr(kelas_wali, 'first') else (kelas_wali[0] if kelas_wali else None)
            elif pendidik.role == 'SUPERADMIN':
                kelas_wali = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
                default_kelas = kelas_wali.first() if hasattr(kelas_wali, 'first') else (kelas_wali[0] if kelas_wali else None)
        elif request.user.is_superuser:
            pendidik, _ = Pendidik.objects.get_or_create(
                user=request.user,
                defaults={
                    'nama_lengkap': request.user.get_full_name() or f"Administrator ({request.user.username})",
                    'role': 'SUPERADMIN',
                    'is_active': True,
                }
            )
            role = 'SUPERADMIN'
            kelas_wali = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
            default_kelas = kelas_wali.first() if hasattr(kelas_wali, 'first') else (kelas_wali[0] if kelas_wali else None)

    return {
        'sekolah_aktif': sekolah,
        'tahun_ajaran_aktif': ta_aktif,
        'semester_aktif': sem_aktif,
        'profil_pendidik': pendidik,
        'user_role': role,
        'kelas_wali_list': kelas_wali,
        'default_kelas': default_kelas,
    }
