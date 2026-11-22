from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.core.models import Sekolah, Pendidik
from apps.master_akademik.models import Kelas, Murid, AnggotaKelas, TahunAjaran, Semester
from apps.kurikulum.models import MataPelajaran, PembelajaranKelas
from apps.penilaian.models import NilaiAkhir, CatatanWaliKelas, Ketidakhadiran

def login_view(request):
    """Halaman login e-Rapor eLHaEs."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Ahlan wa Sahlan, {user.first_name or user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Nama pengguna atau kata sandi tidak sesuai. Silakan periksa kembali.")

    return render(request, 'core/login.html')

def logout_view(request):
    """Keluar dari sistem e-Rapor."""
    logout(request)
    messages.info(request, "Anda telah keluar dari aplikasi e-Rapor.")
    return redirect('login')

@login_required(login_url='login')
def dashboard_view(request):
    """
    Dashboard utama yang menyesuaikan widget dan pintasan fitur
    secara dinamis berdasarkan peran RBAC pengguna yang login.
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    sem_aktif = Semester.objects.filter(is_active=True).first()

    # Statistik Umum
    total_murid = Murid.objects.filter(is_active=True).count()
    total_kelas = Kelas.objects.filter(tahun_ajaran=ta_aktif).count() if ta_aktif else 0
    total_mupel = MataPelajaran.objects.filter(is_active=True).count()
    total_pendidik = Pendidik.objects.filter(is_active=True).count()

    context = {
        'total_murid': total_murid,
        'total_kelas': total_kelas,
        'total_mupel': total_mupel,
        'total_pendidik': total_pendidik,
        'kelas_asuhan': None,
        'murid_kelas_list': [],
        'jadwal_mengajar': [],
        'rekap_semua_kelas': [],
    }

    # Jika Wali Kelas (atau Superadmin)
    if pendidik and pendidik.role == 'WALI_KELAS' or user.is_superuser:
        kelas_wali = Kelas.objects.filter(wali_kelas=pendidik, tahun_ajaran=ta_aktif).first() if pendidik else Kelas.objects.filter(tahun_ajaran=ta_aktif).first()
        if kelas_wali:
            anggota_list = AnggotaKelas.objects.filter(kelas=kelas_wali).select_related('murid').order_by('nomor_absen')
            
            # Hitung progres pengisian
            total_anggota = anggota_list.count()
            catatan_terisi = CatatanWaliKelas.objects.filter(
                anggota_kelas__in=anggota_list, 
                semester=sem_aktif
            ).exclude(catatan='').count() if sem_aktif else 0

            absen_terisi = Ketidakhadiran.objects.filter(
                anggota_kelas__in=anggota_list,
                semester=sem_aktif
            ).count() if sem_aktif else 0

            context['kelas_asuhan'] = kelas_wali
            context['murid_kelas_list'] = anggota_list
            context['total_anggota_kelas'] = total_anggota
            context['catatan_wali_persen'] = int((catatan_terisi / total_anggota * 100)) if total_anggota > 0 else 0
            context['absen_persen'] = int((absen_terisi / total_anggota * 100)) if total_anggota > 0 else 0

    # Jika Guru Mata Pelajaran
    if pendidik:
        jadwal = PembelajaranKelas.objects.filter(
            guru_pengampu=pendidik,
            semester=sem_aktif
        ).select_related('kelas', 'mata_pelajaran')
        context['jadwal_mengajar'] = jadwal

    # Jika Kurikulum atau Kepala Sekolah
    if user.is_superuser or (pendidik and pendidik.role in ['KURIKULUM', 'KEPALA_SEKOLAH']):
        kelas_all = Kelas.objects.filter(tahun_ajaran=ta_aktif).select_related('wali_kelas', 'fase')
        rekap_list = []
        for k in kelas_all:
            jml_murid = k.anggota_list.count()
            rekap_list.append({
                'kelas': k,
                'tingkat': k.tingkat,
                'fase': k.fase.kode,
                'wali': k.wali_kelas.nama_lengkap if k.wali_kelas else 'Belum ditentukan',
                'total_murid': jml_murid,
            })
        context['rekap_semua_kelas'] = rekap_list

    return render(request, 'core/dashboard.html', context)
