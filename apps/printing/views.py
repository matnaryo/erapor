from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.core.decorators import role_required
from apps.core.models import Sekolah
from apps.master_akademik.models import AnggotaKelas, Kelas, Semester, TahunAjaran
from apps.kurikulum.models import PembelajaranKelas
from apps.penilaian.models import (
    NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai,
    PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS', 'KEPALA_SEKOLAH'])
def rapor_print_view(request, anggota_id):
    """
    Mesin Cetak Rapor Resmi 6 Halaman A4 SDIT Luqman Al Hakim Sleman.
    Tunduk mutlak pada aturan batas bebas tinta 2,0 cm di bagian bawah,
    lebar kolom terkunci, thead berulang, dan anti-orphan (titi mangsa/ttd didampingi ketidakhadiran).
    """
    anggota = get_object_or_404(
        AnggotaKelas.objects.select_related('murid', 'kelas', 'kelas__tahun_ajaran', 'kelas__fase', 'kelas__wali_kelas'),
        id=anggota_id
    )
    murid = anggota.murid
    kelas = anggota.kelas
    ta = kelas.tahun_ajaran
    sem = Semester.objects.filter(is_active=True).first()
    sekolah = Sekolah.objects.first() or Sekolah()

    # Ambil 11 nilai mupel resmi
    pembelajaran_list = PembelajaranKelas.objects.filter(
        kelas=kelas,
        semester=sem
    ).select_related('mata_pelajaran').order_by('mata_pelajaran__urutan')

    nilai_dict = {
        n.pembelajaran_kelas_id: n for n in NilaiAkhir.objects.filter(
            anggota_kelas=anggota,
            pembelajaran_kelas__in=pembelajaran_list
        )
    }

    # Distribusi 11 Mata Pelajaran ke Halaman 1, 2, 3
    # Halaman 1: Mupel Umum 1-4 (PAI, Pancasila, BI, MTK)
    # Halaman 2: Mupel Umum 5-8 (IPAS, Seni Rupa, PJOK, B. Inggris)
    # Halaman 3: Mupel Pilihan 9-10 (KKA, B. Arab) & Mulok 11 (B. Jawa)
    mupel_hal1 = []
    mupel_hal2 = []
    mupel_pilihan = []
    mupel_mulok = []

    for p in pembelajaran_list:
        urutan = p.mata_pelajaran.urutan
        n_obj = nilai_dict.get(p.id)
        row = {
            'no': urutan,
            'nama': p.mata_pelajaran.nama,
            'nilai_angka': int(round(n_obj.nilai_angka)) if n_obj and n_obj.nilai_angka is not None else '-',
            'tertinggi': n_obj.capaian_tertinggi if n_obj else '-',
            'perlu': n_obj.capaian_perlu_bimbingan if n_obj else '',
        }
        if urutan in [1, 2, 3, 4]:
            mupel_hal1.append(row)
        elif urutan in [5, 6, 7, 8]:
            mupel_hal2.append(row)
        elif urutan in [9, 10]:
            mupel_pilihan.append(row)
        elif urutan == 11:
            mupel_mulok.append(row)

    # Kokurikuler (Halaman 3)
    koku_obj = KokurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem).first()

    # Catatan Wali Kelas (Halaman 4)
    catatan_obj = CatatanWaliKelas.objects.filter(anggota_kelas=anggota, semester=sem).first()

    # Ekstrakurikuler (Halaman 4 - hanya ekskul yang terisi)
    ekskul_qs = EkstrakurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem).order_by('urutan')
    ekskul_list = [e for e in ekskul_qs if e.kegiatan and e.kegiatan.strip()]
    ekskul_map = {e.urutan: e for e in ekskul_qs}
    ekskul_slots = []
    for i in range(1, 7):
        ekskul_slots.append({
            'no': i,
            'item': ekskul_map.get(i)
        })

    # Prestasi (Halaman 5 - 6 Slot)
    prestasi_qs = PrestasiMurid.objects.filter(anggota_kelas=anggota, semester=sem).order_by('urutan')
    prestasi_map = {p.urutan: p for p in prestasi_qs}
    prestasi_slots = []
    for i in range(1, 7):
        prestasi_slots.append({
            'no': i,
            'item': prestasi_map.get(i)
        })

    # Ketidakhadiran (Halaman 6)
    absen_obj = Ketidakhadiran.objects.filter(anggota_kelas=anggota, semester=sem).first()

    context = {
        'sekolah': sekolah,
        'anggota': anggota,
        'murid': murid,
        'kelas': kelas,
        'ta': ta,
        'sem': sem,
        'mupel_hal1': mupel_hal1,
        'mupel_hal2': mupel_hal2,
        'mupel_pilihan': mupel_pilihan,
        'mupel_mulok': mupel_mulok,
        'koku_obj': koku_obj,
        'catatan_obj': catatan_obj,
        'ekskul_slots': ekskul_slots,
        'ekskul_list': ekskul_list,
        'prestasi_slots': prestasi_slots,
        'absen_obj': absen_obj,
    }
    return render(request, 'printing/rapor_6hal.html', context)


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS', 'KEPALA_SEKOLAH'])
def cover_print_view(request, anggota_id):
    """
    Mesin Cetak Kover Resmi 3 Halaman A4 SDIT Luqman Al Hakim Sleman.
    - Halaman 1: Kover Depan Luar (Logo, Judul, Kotak Nama & NISN).
    - Halaman 2: Lembar Identitas Sekolah.
    - Halaman 3: Lembar Buku Induk Identitas Murid (lengkap pas foto 3x4 & ttd kepala sekolah).
    """
    anggota = get_object_or_404(
        AnggotaKelas.objects.select_related('murid', 'kelas', 'kelas__tahun_ajaran'),
        id=anggota_id
    )
    murid = anggota.murid
    kelas = anggota.kelas
    ta = kelas.tahun_ajaran
    sem = Semester.objects.filter(is_active=True).first()
    sekolah = Sekolah.objects.first() or Sekolah()

    context = {
        'sekolah': sekolah,
        'anggota': anggota,
        'murid': murid,
        'kelas': kelas,
        'ta': ta,
        'sem': sem,
    }
    return render(request, 'printing/cover_3hal.html', context)


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS', 'KEPALA_SEKOLAH'])
def class_print_list_view(request, kelas_id=None):
    """
    Pusat Cetak Dokumen Rapor & Kover 1 Rombongan Belajar.
    Memudahkan pencetakan rapor dan kover per murid secara tertata.
    Superuser / Admin / Kurikulum dapat berganti kelas secara leluasa melalui pilihan kelas.
    Wali Kelas dikunci pada kelas asuhan masing-masing.
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    is_admin = user.is_superuser or (pendidik and pendidik.role in ['SUPERADMIN', 'KURIKULUM', 'KEPALA_SEKOLAH'])

    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()

    if is_admin:
        kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif).select_related('wali_kelas', 'fase').order_by('tingkat', 'nama') if ta_aktif else Kelas.objects.all().select_related('wali_kelas', 'fase').order_by('tingkat', 'nama')
    elif pendidik and pendidik.role == 'WALI_KELAS':
        kelas_list = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).select_related('wali_kelas', 'fase').order_by('tingkat', 'nama') if ta_aktif else pendidik.kelas_asuhan.all().select_related('wali_kelas', 'fase').order_by('tingkat', 'nama')
    else:
        kelas_list = Kelas.objects.none()

    # Pergantian kelas melalui query param ?kelas=
    target_param = request.GET.get('kelas')
    if target_param:
        try:
            target_id = int(target_param)
            if target_id != kelas_id:
                return redirect('class_print_list', kelas_id=target_id)
        except (ValueError, TypeError):
            pass

    # Jika kelas_id belum diberikan, ambil kelas pertama yang tersedia
    if not kelas_id:
        if kelas_list.exists():
            return redirect('class_print_list', kelas_id=kelas_list.first().id)
        else:
            messages.error(request, "Belum ada rombel kelas yang terdaftar.")
            return redirect('dashboard')

    kelas = get_object_or_404(Kelas.objects.select_related('wali_kelas', 'fase', 'tahun_ajaran'), id=kelas_id)

    # Validasi wewenang jika wali kelas murni (bukan admin)
    if not is_admin and pendidik and pendidik.role == 'WALI_KELAS':
        if kelas.wali_kelas_id != pendidik.id:
            messages.error(request, "Akses ditolak: Anda hanya berwenang mencetak dokumen untuk kelas asuhan Anda.")
            return redirect('dashboard')

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    context = {
        'kelas': kelas,
        'kelas_list': kelas_list,
        'is_admin': is_admin,
        'sem_aktif': sem_aktif,
        'anggota_list': anggota_list,
    }
    return render(request, 'printing/class_print_list.html', context)
