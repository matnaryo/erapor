from .models import Sekolah
from apps.master_akademik.models import TahunAjaran, Semester

def global_school_context(request):
    """
    Context processor global untuk seluruh template:
    Profil sekolah, tahun ajaran aktif, semester aktif, dan profil pendidik.
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
            role = 'SUPERADMIN'
        elif pendidik:
            role = pendidik.role
            if pendidik.role == 'WALI_KELAS' or request.user.is_superuser:
                kelas_wali = pendidik.kelas_asuhan.all()

    return {
        'sekolah_aktif': sekolah,
        'tahun_ajaran_aktif': ta_aktif,
        'semester_aktif': sem_aktif,
        'profil_pendidik': pendidik,
        'user_role': role,
        'kelas_wali_list': kelas_wali,
    }
