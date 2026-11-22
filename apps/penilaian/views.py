import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.core.decorators import role_required
from apps.master_akademik.models import Kelas, AnggotaKelas, Semester, TahunAjaran
from apps.kurikulum.models import PembelajaranKelas, MataPelajaran
from .models import (
    NilaiAkhir, NilaiTP, KokurikulerNilai, EkstrakurikulerNilai, 
    PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
)
from .services import (
    get_kktp_and_predikat, generate_capaian_kompetensi, ensure_pembelajaran_kelas,
    get_tp_descriptions, calculate_from_tp_scores
)
from apps.ai_assistant.ollama_client import generate_capaian_kompetensi_ai

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
    Formulir matriks nilai rapor interaktif (layaknya spreadsheet/Excel):
    - Tabel kiri: No Presensi & Nama Murid.
    - Kolom matriks: 15 Kolom Tujuan Pembelajaran (TP 1 s/d TP 15).
    - Kolom hasil: Nilai Akhir (rata-rata terhitung), Predikat KKTP, Capaian Tertinggi, Capaian Terendah.
    - Dilengkapi integrasi Asisten AI untuk menyempurnakan narasi rapor.
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
    tp_descriptions = get_tp_descriptions(pembelajaran)

    # Ambil nilai yang sudah ada
    nilai_dict = {
        n.anggota_kelas_id: n for n in NilaiAkhir.objects.filter(
            pembelajaran_kelas=pembelajaran,
            anggota_kelas__in=anggota_list
        )
    }

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'save_tp_desc':
            # Simpan keterangan deskripsi TP 1-15
            custom_tp = {}
            for i in range(1, 16):
                val = request.POST.get(f"tp_desc_{i}", "").strip()
                if val:
                    custom_tp[str(i)] = val
            pembelajaran.tp_deskripsi_json = custom_tp
            pembelajaran.save()
            messages.success(request, f"Keterangan Tujuan Pembelajaran (TP 1 - 15) untuk {mupel.nama} berhasil diperbarui.")
            return redirect('nilai_mupel_input', pembelajaran_id=pembelajaran.id)

        # Action == 'save' atau 'auto_generate'
        for anggota in anggota_list:
            prefix = f"murid_{anggota.id}_"
            
            # Kumpulkan nilai 15 TP
            tp_values = {}
            for i in range(1, 16):
                tp_val_str = request.POST.get(f"{prefix}tp_{i}", "").strip().replace(',', '.')
                if tp_val_str != "":
                    try:
                        v = float(tp_val_str)
                        if 0 <= v <= 100:
                            tp_values[str(i)] = v
                    except ValueError:
                        pass

            na_manual_str = request.POST.get(f"{prefix}nilai", "").strip().replace(',', '.')
            capaian_tertinggi_manual = request.POST.get(f"{prefix}tertinggi", "").strip()
            capaian_perlu_manual = request.POST.get(f"{prefix}perlu", "").strip()

            calc_na, calc_pred, calc_tert, calc_perlu, max_tp, min_tp = calculate_from_tp_scores(
                tp_values, tp_descriptions, mupel, fase
            )

            if tp_values:
                nilai_angka = calc_na
                predikat = calc_pred

                if action == 'auto_generate' or not capaian_tertinggi_manual:
                    capaian_tertinggi = calc_tert
                else:
                    capaian_tertinggi = capaian_tertinggi_manual

                if action == 'auto_generate' or not capaian_perlu_manual:
                    capaian_perlu = calc_perlu
                else:
                    capaian_perlu = capaian_perlu_manual

                NilaiAkhir.objects.update_or_create(
                    anggota_kelas=anggota,
                    pembelajaran_kelas=pembelajaran,
                    defaults={
                        'nilai_angka': nilai_angka,
                        'predikat': predikat,
                        'capaian_tertinggi': capaian_tertinggi,
                        'capaian_perlu_bimbingan': capaian_perlu,
                        'nilai_tp': tp_values
                    }
                )

                # Sinkronisasi ke model relasional NilaiTP
                for i in range(1, 16):
                    str_i = str(i)
                    if str_i in tp_values:
                        NilaiTP.objects.update_or_create(
                            anggota_kelas=anggota,
                            pembelajaran_kelas=pembelajaran,
                            tp_nomor=i,
                            defaults={'nilai': Decimal(str(tp_values[str_i]))}
                        )
                    else:
                        NilaiTP.objects.filter(
                            anggota_kelas=anggota,
                            pembelajaran_kelas=pembelajaran,
                            tp_nomor=i
                        ).delete()

            elif na_manual_str:
                # Fallback jika hanya menginput nilai akhir secara manual
                try:
                    na_val = float(na_manual_str)
                    pred, _ = get_kktp_and_predikat(na_val, mupel, fase)
                    NilaiAkhir.objects.update_or_create(
                        anggota_kelas=anggota,
                        pembelajaran_kelas=pembelajaran,
                        defaults={
                            'nilai_angka': na_val,
                            'predikat': pred,
                            'capaian_tertinggi': capaian_tertinggi_manual or f"Murid menunjukkan penguasaan yang baik dalam materi {mupel.nama}.",
                            'capaian_perlu_bimbingan': capaian_perlu_manual,
                            'nilai_tp': {}
                        }
                    )
                except ValueError:
                    pass

        if action == 'auto_generate':
            messages.success(request, f"Capaian tertinggi dan terendah untuk {mupel.nama} berhasil dirumuskan otomatis dari nilai TP.")
        else:
            messages.success(request, f"Matriks nilai rapor {mupel.nama} Kelas {kelas.nama} berhasil disimpan!")
        
        return redirect('nilai_mupel_input', pembelajaran_id=pembelajaran.id)

    # Siapkan data baris murid untuk matriks
    row_data = []
    for anggota in anggota_list:
        nilai_obj = nilai_dict.get(anggota.id)
        tp_dict = nilai_obj.nilai_tp if nilai_obj and nilai_obj.nilai_tp else {}
        
        # Susun nilai per TP 1..15
        tp_cells = []
        for i in range(1, 16):
            val = tp_dict.get(str(i)) or tp_dict.get(i)
            val_formatted = ""
            if val is not None:
                try:
                    val_float = float(val)
                    val_formatted = f"{val_float:.0f}" if val_float.is_integer() else f"{val_float:.2f}"
                except (ValueError, TypeError):
                    val_formatted = str(val)
            tp_cells.append({
                'tp_num': i,
                'value': val_formatted,
            })

        row_data.append({
            'anggota': anggota,
            'nilai': nilai_obj,
            'tp_cells': tp_cells,
        })

    # Pembelajaran lain di kelas ini untuk tabs switcher
    daftar_mupel_kelas = PembelajaranKelas.objects.filter(
        kelas=kelas,
        semester=sem
    ).select_related('mata_pelajaran').order_by('mata_pelajaran__urutan')

    context = {
        'pembelajaran': pembelajaran,
        'kelas': kelas,
        'mupel': mupel,
        'fase': fase,
        'sem': sem,
        'row_data': row_data,
        'tp_descriptions': tp_descriptions,
        'tp_descriptions_json': json.dumps(tp_descriptions),
        'tp_range': list(range(1, 16)),
        'daftar_mupel_kelas': daftar_mupel_kelas,
    }
    return render(request, 'penilaian/nilai_mupel_input.html', context)


@login_required(login_url='login')
def api_generate_capaian_ai_view(request):
    """
    API JSON untuk menghasilkan narasi Capaian Tertinggi & Capaian Perlu Bimbingan
    secara dinamis menggunakan Local AI Qwen Instruct berdasarkan nilai TP murid.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method POST required.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    pembelajaran_id = data.get('pembelajaran_id')
    anggota_id = data.get('anggota_id')
    
    pembelajaran = get_object_or_404(
        PembelajaranKelas.objects.select_related('kelas', 'mata_pelajaran', 'kelas__fase', 'semester'),
        id=pembelajaran_id
    )
    anggota = get_object_or_404(AnggotaKelas.objects.select_related('murid'), id=anggota_id)
    tp_scores = data.get('tp_scores', {})
    
    tp_descriptions = get_tp_descriptions(pembelajaran)
    calc_na, calc_pred, calc_tert, calc_perlu, max_tp, min_tp = calculate_from_tp_scores(
        tp_scores, tp_descriptions, pembelajaran.mata_pelajaran, pembelajaran.kelas.fase
    )

    if not max_tp:
        return JsonResponse({
            'status': 'error',
            'message': 'Belum ada nilai TP yang diisi untuk murid ini.'
        }, status=400)

    max_desc = tp_descriptions.get(max_tp, f"materi TP {max_tp}")
    min_desc = tp_descriptions.get(min_tp, f"materi TP {min_tp}") if min_tp and min_tp != max_tp else ""

    tertinggi_ai, perlu_ai, is_ai = generate_capaian_kompetensi_ai(
        nama_murid=anggota.murid.nama_lengkap,
        mupel_nama=pembelajaran.mata_pelajaran.nama,
        nilai_akhir=calc_na,
        predikat=calc_pred,
        max_desc=max_desc,
        min_desc=min_desc,
        timeout=15
    )

    return JsonResponse({
        'status': 'success',
        'nilai_akhir': calc_na,
        'predikat': calc_pred,
        'tertinggi': tertinggi_ai or calc_tert,
        'perlu': perlu_ai or calc_perlu,
        'is_ai': is_ai,
        'max_tp': max_tp,
        'min_tp': min_tp,
    })


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
