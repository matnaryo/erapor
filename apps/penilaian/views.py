from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.core.decorators import role_required
from apps.master_akademik.models import Kelas, AnggotaKelas, Semester, TahunAjaran
from apps.kurikulum.models import PembelajaranKelas, MataPelajaran
from .models import NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
from .services import get_kktp_and_predikat, generate_capaian_kompetensi, ensure_pembelajaran_kelas

@login_required(login_url='login')
def nilai_matrix_view(request):
    """
    Tampilan Matriks Penilaian: Memilih Kelas dan Semester untuk melihat status kelengkapan nilai rapor.
    """
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    sem_aktif = Semester.objects.filter(is_active=True).first()
    
    kelas_id = request.GET.get('kelas')
    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif).order_by('tingkat', 'nama')
    
    selected_kelas = Kelas.objects.filter(id=kelas_id).first() if kelas_id else kelas_list.first()

    pembelajaran_list = []
    anggota_list = []
    if selected_kelas and sem_aktif:
        ensure_pembelajaran_kelas(selected_kelas, sem_aktif, selected_kelas.wali_kelas)
        pembelajaran_list = PembelajaranKelas.objects.filter(
            kelas=selected_kelas,
            semester=sem_aktif
        ).select_related('mata_pelajaran', 'guru_pengampu').order_by('mata_pelajaran__urutan')
        
        anggota_list = AnggotaKelas.objects.filter(kelas=selected_kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    context = {
        'ta_aktif': ta_aktif,
        'sem_aktif': sem_aktif,
        'kelas_list': kelas_list,
        'selected_kelas': selected_kelas,
        'pembelajaran_list': pembelajaran_list,
        'anggota_list': anggota_list,
    }
    return render(request, 'penilaian/nilai_matrix.html', context)


@login_required(login_url='login')
def nilai_mupel_input_view(request, pembelajaran_id):
    """
    Formulir input nilai akhir dan capaian kompetensi satu mata pelajaran untuk seluruh murid dalam satu kelas.
    """
    pembelajaran = get_object_or_404(
        PembelajaranKelas.objects.select_related('kelas', 'mata_pelajaran', 'semester', 'kelas__fase'),
        id=pembelajaran_id
    )
    kelas = pembelajaran.kelas
    fase = kelas.fase
    sem = pembelajaran.semester
    mupel = pembelajaran.mata_pelajaran

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    # Ambil nilai yang sudah ada atau buat placeholder
    nilai_dict = {
        n.anggota_kelas_id: n for n in NilaiAkhir.objects.filter(
            pembelajaran_kelas=pembelajaran,
            anggota_kelas__in=anggota_list
        )
    }

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        
        for anggota in anggota_list:
            prefix = f"murid_{anggota.id}_"
            nilai_angka_raw = request.POST.get(f"{prefix}nilai", "").strip().replace(',', '.')
            capaian_tertinggi = request.POST.get(f"{prefix}tertinggi", "").strip()
            capaian_perlu = request.POST.get(f"{prefix}perlu", "").strip()

            if nilai_angka_raw:
                try:
                    nilai_angka = float(nilai_angka_raw)
                    predikat, _ = get_kktp_and_predikat(nilai_angka, mupel, fase)

                    if action == 'auto_generate':
                        predikat, capaian_tertinggi, capaian_perlu = generate_capaian_kompetensi(
                            nilai_angka, mupel, fase, semester=sem.semester, tingkat=kelas.tingkat
                        )

                    NilaiAkhir.objects.update_or_create(
                        anggota_kelas=anggota,
                        pembelajaran_kelas=pembelajaran,
                        defaults={
                            'nilai_angka': nilai_angka,
                            'predikat': predikat,
                            'capaian_tertinggi': capaian_tertinggi,
                            'capaian_perlu_bimbingan': capaian_perlu
                        }
                    )
                except ValueError:
                    pass

        if action == 'auto_generate':
            messages.success(request, f"Capaian kompetensi otomatis untuk {mupel.nama} berhasil digenerate berdasarkan KKTP & TP.")
        else:
            messages.success(request, f"Nilai akhir {mupel.nama} kelas {kelas.nama} berhasil disimpan.")
        
        return redirect('nilai_mupel_input', pembelajaran_id=pembelajaran.id)

    # Siapkan row data untuk template
    row_data = []
    for anggota in anggota_list:
        nilai_obj = nilai_dict.get(anggota.id)
        row_data.append({
            'anggota': anggota,
            'nilai': nilai_obj,
        })

    context = {
        'pembelajaran': pembelajaran,
        'kelas': kelas,
        'mupel': mupel,
        'fase': fase,
        'sem': sem,
        'row_data': row_data,
    }
    return render(request, 'penilaian/nilai_mupel_input.html', context)


@login_required(login_url='login')
def kokurikuler_input_view(request, kelas_id):
    """
    Formulir input nilai Kokurikuler (aspek pembiasaan ibadah dan adab islami) per kelas.
    """
    kelas = get_object_or_404(Kelas, id=kelas_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    koku_dict = {
        k.anggota_kelas_id: k for k in KokurikulerNilai.objects.filter(
            semester=sem_aktif,
            anggota_kelas__in=anggota_list
        )
    }

    default_deskripsi = (
        "Murid sangat baik dalam membiasakan sholat dhuha dan sholat berjamaah tepat waktu dengan tertib, "
        "menunjukkan peningkatan hafalan tahfidz juz 30 dengan tartil ceria, konsisten membiasakan adab makan sehat "
        "halalan thoyyiban sambil duduk dan berdoa, serta aktif berolahraga dengan penuh sportivitas."
    )

    if request.method == 'POST':
        for anggota in anggota_list:
            pred = request.POST.get(f"koku_{anggota.id}_predikat", "A")
            desk = request.POST.get(f"koku_{anggota.id}_deskripsi", "").strip() or default_deskripsi
            KokurikulerNilai.objects.update_or_create(
                anggota_kelas=anggota,
                semester=sem_aktif,
                aspek="Kokurikuler",
                defaults={
                    'predikat': pred,
                    'deskripsi': desk
                }
            )
        messages.success(request, f"Nilai Kokurikuler kelas {kelas.nama} berhasil disimpan.")
        return redirect('kokurikuler_input', kelas_id=kelas.id)

    row_data = []
    for anggota in anggota_list:
        koku = koku_dict.get(anggota.id)
        row_data.append({
            'anggota': anggota,
            'predikat': koku.predikat if koku else 'A',
            'deskripsi': koku.deskripsi if koku else default_deskripsi,
        })

    context = {
        'kelas': kelas,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
    }
    return render(request, 'penilaian/kokurikuler_input.html', context)


@login_required(login_url='login')
def ekskul_prestasi_input_view(request, anggota_id):
    """
    Formulir input Ekstrakurikuler (maks 6 baris) & Prestasi (maks 6 baris) per murid.
    Sesuai layout cetak rapor Halaman 4 dan Halaman 5.
    """
    anggota = get_object_or_404(AnggotaKelas.objects.select_related('murid', 'kelas'), id=anggota_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()

    ekskul_list = EkstrakurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem_aktif).order_by('urutan')
    prestasi_list = PrestasiMurid.objects.filter(anggota_kelas=anggota, semester=sem_aktif).order_by('urutan')

    ekskul_map = {e.urutan: e for e in ekskul_list}
    prestasi_map = {p.urutan: p for p in prestasi_list}

    if request.method == 'POST':
        # Simpan 6 baris ekskul
        for i in range(1, 7):
            keg = request.POST.get(f"ekskul_{i}_kegiatan", "").strip()
            pred = request.POST.get(f"ekskul_{i}_predikat", "-").strip()
            ket = request.POST.get(f"ekskul_{i}_keterangan", "").strip()
            if keg:
                EkstrakurikulerNilai.objects.update_or_create(
                    anggota_kelas=anggota,
                    semester=sem_aktif,
                    urutan=i,
                    defaults={'kegiatan': keg, 'predikat': pred, 'keterangan': ket}
                )
            else:
                EkstrakurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem_aktif, urutan=i).delete()

        # Simpan 6 baris prestasi
        for i in range(1, 7):
            jenis = request.POST.get(f"prestasi_{i}_jenis", "").strip()
            ket = request.POST.get(f"prestasi_{i}_keterangan", "").strip()
            if jenis:
                PrestasiMurid.objects.update_or_create(
                    anggota_kelas=anggota,
                    semester=sem_aktif,
                    urutan=i,
                    defaults={'jenis_prestasi': jenis, 'keterangan': ket}
                )
            else:
                PrestasiMurid.objects.filter(anggota_kelas=anggota, semester=sem_aktif, urutan=i).delete()

        messages.success(request, f"Data Ekstrakurikuler & Prestasi untuk {anggota.murid.nama_lengkap} berhasil disimpan.")
        return redirect('ekskul_prestasi_input', anggota_id=anggota.id)

    # Bentuk 6 baris slot
    ekskul_slots = []
    for i in range(1, 7):
        ekskul_slots.append({
            'urutan': i,
            'item': ekskul_map.get(i),
        })

    prestasi_slots = []
    for i in range(1, 7):
        prestasi_slots.append({
            'urutan': i,
            'item': prestasi_map.get(i),
        })

    context = {
        'anggota': anggota,
        'sem_aktif': sem_aktif,
        'ekskul_slots': ekskul_slots,
        'prestasi_slots': prestasi_slots,
    }
    return render(request, 'penilaian/ekskul_prestasi_input.html', context)


@login_required(login_url='login')
def rekap_absen_input_view(request, kelas_id):
    """
    Formulir input Rekapitulasi Ketidakhadiran (Sakit, Izin, Alpa) per kelas.
    Ditampilkan di Halaman 6 dokumen rapor.
    """
    kelas = get_object_or_404(Kelas, id=kelas_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    absen_dict = {
        a.anggota_kelas_id: a for a in Ketidakhadiran.objects.filter(
            semester=sem_aktif,
            anggota_kelas__in=anggota_list
        )
    }

    if request.method == 'POST':
        for anggota in anggota_list:
            sakit = int(request.POST.get(f"absen_{anggota.id}_sakit", 0) or 0)
            izin = int(request.POST.get(f"absen_{anggota.id}_izin", 0) or 0)
            alpa = int(request.POST.get(f"absen_{anggota.id}_alpa", 0) or 0)

            Ketidakhadiran.objects.update_or_create(
                anggota_kelas=anggota,
                semester=sem_aktif,
                defaults={
                    'sakit': sakit,
                    'izin': izin,
                    'tanpa_keterangan': alpa
                }
            )
        messages.success(request, f"Rekap ketidakhadiran kelas {kelas.nama} berhasil disimpan.")
        return redirect('rekap_absen_input', kelas_id=kelas.id)

    row_data = []
    for anggota in anggota_list:
        absen = absen_dict.get(anggota.id)
        row_data.append({
            'anggota': anggota,
            'sakit': absen.sakit if absen else 0,
            'izin': absen.izin if absen else 0,
            'alpa': absen.tanpa_keterangan if absen else 0,
        })

    context = {
        'kelas': kelas,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
    }
    return render(request, 'penilaian/rekap_absen_input.html', context)


@login_required(login_url='login')
def catatan_wali_input_view(request, kelas_id):
    """
    Formulir input Catatan Naratif Wali Kelas (Halaman 4 cetak rapor).
    """
    kelas = get_object_or_404(Kelas, id=kelas_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    catatan_dict = {
        c.anggota_kelas_id: c for c in CatatanWaliKelas.objects.filter(
            semester=sem_aktif,
            anggota_kelas__in=anggota_list
        )
    }

    default_template = (
        "Alhamdulillaah, ananda menunjukkan semangat belajar dan pembiasaan adab yang sangat membanggakan di semester ini, "
        "khususnya dalam ketekunan sholat dhuha berjamaah dan hafalan tahfidz juz 30. Tingkatkan konsentrasi dan ketelitian "
        "dalam latihan mandiri di rumah. Semoga Allah senantiasa menjaga ananda menjadi anak yang sholih, cerdas, dan senantiasa "
        "berbakti kepada orang tua. Barakallahu fiik."
    )

    if request.method == 'POST':
        for anggota in anggota_list:
            catatan = request.POST.get(f"catatan_{anggota.id}", "").strip()
            if catatan:
                CatatanWaliKelas.objects.update_or_create(
                    anggota_kelas=anggota,
                    semester=sem_aktif,
                    defaults={'catatan': catatan}
                )
        messages.success(request, f"Catatan wali kelas untuk kelas {kelas.nama} berhasil disimpan.")
        return redirect('catatan_wali_input', kelas_id=kelas.id)

    row_data = []
    for anggota in anggota_list:
        cat = catatan_dict.get(anggota.id)
        row_data.append({
            'anggota': anggota,
            'catatan': cat.catatan if cat else default_template,
            'is_ai': cat.is_generated_by_ai if cat else False,
        })

    context = {
        'kelas': kelas,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
    }
    return render(request, 'penilaian/catatan_wali_input.html', context)
