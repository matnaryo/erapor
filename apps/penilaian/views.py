import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.core.decorators import role_required
from apps.master_akademik.models import Kelas, AnggotaKelas, Semester, TahunAjaran
from apps.kurikulum.models import PembelajaranKelas, MataPelajaran, TPKokurikuler
from .models import (
    NilaiAkhir, NilaiTP, KokurikulerNilai, EkstrakurikulerNilai, 
    PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
)
from .services import (
    get_kktp_and_predikat, generate_capaian_kompetensi, ensure_pembelajaran_kelas,
    get_tp_descriptions, calculate_from_tp_scores,
    get_koku_predikat_and_ket, generate_kokurikuler_combined_deskripsi
)
from apps.ai_assistant.ollama_client import generate_capaian_kompetensi_ai

@login_required(login_url='login')
def nilai_matrix_view(request):
    """
    Tampilan Matriks Penilaian: Memilih Kelas dan Semester untuk melihat status kelengkapan nilai rapor.
    """
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    sem_aktif = Semester.objects.filter(is_active=True).first()
    pendidik = getattr(request.user, 'profil_pendidik', None)
    
    kelas_id = request.GET.get('kelas')
    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif).order_by('tingkat', 'nama')

    # Jika Wali Kelas, kunci kelas HANYA ke kelas asuhannya (wali kelas bertanggung jawab pada kelasnya masing-masing)
    if pendidik and pendidik.role == 'WALI_KELAS':
        kelas_asuhan = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).first() or pendidik.kelas_asuhan.first()
        selected_kelas = kelas_asuhan
        kelas_list = Kelas.objects.filter(id=kelas_asuhan.id) if kelas_asuhan else Kelas.objects.none()
    # Jika Guru Mapel, filter hanya kelas yang diajar oleh guru tersebut
    elif pendidik and pendidik.role == 'GURU_MAPEL':
        ampu_kelas_ids = PembelajaranKelas.objects.filter(
            guru_pengampu=pendidik,
            semester=sem_aktif
        ).values_list('kelas_id', flat=True).distinct()
        if not ampu_kelas_ids.exists():
            ampu_kelas_ids = PembelajaranKelas.objects.filter(
                guru_pengampu=pendidik
            ).values_list('kelas_id', flat=True).distinct()
        kelas_list = kelas_list.filter(id__in=ampu_kelas_ids)
        selected_kelas = Kelas.objects.filter(id=kelas_id).first() if kelas_id else kelas_list.first()
    else:
        selected_kelas = Kelas.objects.filter(id=kelas_id).first() if kelas_id else kelas_list.first()

    pembelajaran_list = []
    anggota_list = []
    if selected_kelas and sem_aktif:
        ensure_pembelajaran_kelas(selected_kelas, sem_aktif, selected_kelas.wali_kelas)
        pembelajaran_qs = PembelajaranKelas.objects.filter(
            kelas=selected_kelas,
            semester=sem_aktif
        ).select_related('mata_pelajaran', 'guru_pengampu').order_by('mata_pelajaran__urutan')
        
        # Untuk Guru Mapel, sembunyikan mata pelajaran yang tidak diampu
        if pendidik and pendidik.role == 'GURU_MAPEL':
            pembelajaran_qs = pembelajaran_qs.filter(guru_pengampu=pendidik)

        pembelajaran_list = pembelajaran_qs
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

    pendidik = getattr(request.user, 'profil_pendidik', None)

    # Proteksi RBAC: Guru Mapel hanya dapat mengelola mupel yang diampu
    if pendidik and pendidik.role == 'GURU_MAPEL':
        if pembelajaran.guru_pengampu_id != pendidik.id:
            messages.error(request, f"Akses ditolak: Anda tidak mengampu mata pelajaran {mupel.nama} di Kelas {kelas.nama}.")
            return redirect('nilai_matrix')

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

    # Pembelajaran lain di kelas ini untuk tabs switcher (difilter untuk Guru Mapel)
    daftar_mupel_qs = PembelajaranKelas.objects.filter(
        kelas=kelas,
        semester=sem
    ).select_related('mata_pelajaran').order_by('mata_pelajaran__urutan')

    if pendidik and pendidik.role == 'GURU_MAPEL':
        daftar_mupel_qs = daftar_mupel_qs.filter(guru_pengampu=pendidik)

    daftar_mupel_kelas = daftar_mupel_qs

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
    secara dinamis menggunakan Local AI Ollama qwen2.5:1.5b berdasarkan nilai TP murid.
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
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def kokurikuler_input_view(request, kelas_id=None):
    """
    Submenu Penilaian Kokurikuler:
    Formulir input / review narasi & predikat capaian Kokurikuler per kelas.
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()

    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
    if pendidik and pendidik.role == 'WALI_KELAS':
        kelas_asuhan = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).first() or pendidik.kelas_asuhan.first()
        target_kelas_id = kelas_asuhan.id if kelas_asuhan else None
        kelas_list = Kelas.objects.filter(id=kelas_asuhan.id) if kelas_asuhan else Kelas.objects.none()
    else:
        target_kelas_id = kelas_id or request.GET.get('kelas') or (kelas_list.first().id if kelas_list.exists() else None)

    kelas = get_object_or_404(Kelas, id=target_kelas_id) if target_kelas_id else None
    if not kelas:
        messages.error(request, "Belum ada rombel kelas yang aktif.")
        return redirect('dashboard')

    if pendidik and pendidik.role == 'WALI_KELAS':
        if kelas.wali_kelas_id != pendidik.id and not user.is_superuser:
            messages.error(request, "Anda hanya berwenang mengelola data kelas yang Anda ampu sebagai wali kelas.")
            return redirect('dashboard')

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    koku_dict = {
        k.anggota_kelas_id: k for k in KokurikulerNilai.objects.filter(
            semester=sem_aktif,
            anggota_kelas__in=anggota_list,
            aspek="Kokurikuler"
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
            k_obj = koku_dict.get(anggota.id)
            KokurikulerNilai.objects.update_or_create(
                anggota_kelas=anggota,
                semester=sem_aktif,
                aspek="Kokurikuler",
                defaults={
                    'predikat': pred,
                    'deskripsi': desk,
                    'nilai_angka': k_obj.nilai_angka if k_obj else 0,
                    'tp_scores': k_obj.tp_scores if k_obj else {}
                }
            )
        messages.success(request, f"Alhamdulillaah, Penilaian Kokurikuler kelas {kelas.nama} berhasil disimpan.")
        return redirect('kokurikuler_input', kelas_id=kelas.id)

    row_data = []
    for anggota in anggota_list:
        koku = koku_dict.get(anggota.id)
        row_data.append({
            'anggota': anggota,
            'predikat': koku.predikat if koku else 'A',
            'deskripsi': koku.deskripsi if koku else default_deskripsi,
            'nilai_angka': koku.nilai_angka if koku and koku.nilai_angka > 0 else '',
        })

    context = {
        'kelas': kelas,
        'kelas_list': kelas_list,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
    }
    return render(request, 'penilaian/kokurikuler_input.html', context)


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def kokurikuler_matrix_view(request, kelas_id=None):
    """
    Submenu Matriks Kokurikuler:
    Tabel spreadsheet penilaian Kokurikuler 7 kolom TP per rombel kelas (maksimal 7 kolom TP).
    Dilengkapi live auto-calculation rata-rata, predikat, dan perumusan narasi deskripsi capaian rapor.
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()

    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
    if pendidik and pendidik.role == 'WALI_KELAS':
        kelas_asuhan = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).first() or pendidik.kelas_asuhan.first()
        target_kelas_id = kelas_asuhan.id if kelas_asuhan else None
        kelas_list = Kelas.objects.filter(id=kelas_asuhan.id) if kelas_asuhan else Kelas.objects.none()
    else:
        target_kelas_id = kelas_id or request.GET.get('kelas') or (kelas_list.first().id if kelas_list.exists() else None)

    selected_kelas = get_object_or_404(Kelas, id=target_kelas_id) if target_kelas_id else None

    if pendidik and pendidik.role == 'WALI_KELAS' and selected_kelas:
        if selected_kelas.wali_kelas_id != pendidik.id and not user.is_superuser:
            messages.error(request, "Anda hanya berwenang mengelola data kelas yang Anda ampu sebagai wali kelas.")
            return redirect('dashboard')

    row_data = []
    tp_descriptions = {}
    tp_range = list(range(1, 8))

    if selected_kelas:
        sem_num = sem_aktif.semester if sem_aktif else 1
        tp_qs = TPKokurikuler.objects.filter(tingkat=selected_kelas.tingkat, semester=sem_num).order_by('urutan', 'nomor')
        for tp in tp_qs:
            tp_descriptions[tp.nomor] = tp.deskripsi

        for i in range(1, 8):
            if i not in tp_descriptions:
                tp_descriptions[i] = f"Tujuan Pembelajaran Kokurikuler {i}"

        anggota_list = AnggotaKelas.objects.filter(kelas=selected_kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')
        koku_dict = {
            k.anggota_kelas_id: k for k in KokurikulerNilai.objects.filter(
                anggota_kelas__in=anggota_list,
                semester=sem_aktif,
                aspek="Kokurikuler"
            )
        }

        if request.method == 'POST':
            for a in anggota_list:
                tp_scores = {}
                tp_data_for_desc = []
                all_averages = []

                for i in range(1, 8):
                    raw_obs = request.POST.get(f"murid_{a.id}_tp_{i}_obs", "").strip().replace(',', '.')
                    raw_juri = request.POST.get(f"murid_{a.id}_tp_{i}_juri", "").strip().replace(',', '.')
                    raw_legacy = request.POST.get(f"murid_{a.id}_tp_{i}", "").strip().replace(',', '.')

                    if not raw_obs and not raw_juri and raw_legacy:
                        raw_obs = raw_legacy
                        raw_juri = raw_legacy

                    obs_val = None
                    juri_val = None
                    if raw_obs != "":
                        try:
                            o = float(raw_obs)
                            obs_val = min(4.0, round(o / 25.0, 2)) if o > 4.0 else round(o, 2)
                        except ValueError:
                            pass
                    if raw_juri != "":
                        try:
                            j = float(raw_juri)
                            juri_val = min(4.0, round(j / 25.0, 2)) if j > 4.0 else round(j, 2)
                        except ValueError:
                            pass

                    if obs_val is not None and juri_val is not None:
                        avg_i = round((obs_val + juri_val) / 2.0, 2)
                    elif obs_val is not None:
                        avg_i = obs_val
                    elif juri_val is not None:
                        avg_i = juri_val
                    else:
                        avg_i = None

                    if avg_i is not None:
                        pred_i, ket_i = get_koku_predikat_and_ket(avg_i)
                        tp_scores[str(i)] = avg_i
                        tp_scores[f"{i}_obs"] = obs_val
                        tp_scores[f"{i}_juri"] = juri_val
                        tp_scores[f"{i}_detail"] = {
                            'obs': obs_val,
                            'juri': juri_val,
                            'avg': avg_i,
                            'predikat': pred_i,
                            'ket': ket_i
                        }
                        tp_data_for_desc.append({
                            'nomor': i,
                            'avg': avg_i,
                            'predikat': pred_i,
                            'ket': ket_i,
                            'deskripsi': tp_descriptions.get(i, f"aspek ke-{i}")
                        })
                        all_averages.append(avg_i)

                overall_avg = round(sum(all_averages) / len(all_averages), 2) if all_averages else 0.0
                overall_pred, overall_ket = get_koku_predikat_and_ket(overall_avg)

                user_pred = request.POST.get(f"murid_{a.id}_predikat", "").strip()
                if user_pred:
                    overall_pred = user_pred

                user_desk = request.POST.get(f"murid_{a.id}_deskripsi", "").strip()
                if user_desk:
                    final_desk = user_desk
                elif tp_data_for_desc:
                    final_desk = generate_kokurikuler_combined_deskripsi(tp_data_for_desc)
                else:
                    final_desk = "Murid sangat baik dalam membiasakan ibadah dan adab islami di sekolah."

                KokurikulerNilai.objects.update_or_create(
                    anggota_kelas=a,
                    semester=sem_aktif,
                    aspek="Kokurikuler",
                    defaults={
                        'nilai_angka': overall_avg,
                        'tp_scores': tp_scores,
                        'predikat': overall_pred,
                        'deskripsi': final_desk
                    }
                )

            messages.success(request, f"Alhamdulillaah, Matriks Nilai Kokurikuler kelas {selected_kelas.nama} berhasil disimpan.")
            return redirect(f"{request.path}?kelas={selected_kelas.id}")

        for a in anggota_list:
            k = koku_dict.get(a.id)
            scores = k.tp_scores if k and isinstance(k.tp_scores, dict) else {}

            tp_row_data = []
            tp_data_for_desc = []
            for i in range(1, 8):
                detail = scores.get(f"{i}_detail") or (scores.get(str(i)) if isinstance(scores.get(str(i)), dict) else {})
                obs_raw = scores.get(f"{i}_obs", detail.get('obs', ''))
                juri_raw = scores.get(f"{i}_juri", detail.get('juri', ''))

                if obs_raw == '' and juri_raw == '':
                    legacy_val = scores.get(str(i))
                    if legacy_val is not None and not isinstance(legacy_val, dict):
                        try:
                            val_flt = float(legacy_val)
                            if val_flt > 4.0:
                                val_flt = round(val_flt / 25.0, 2)
                            obs_raw = val_flt
                            juri_raw = val_flt
                        except (ValueError, TypeError):
                            pass

                try:
                    o = float(obs_raw) if obs_raw != '' and obs_raw is not None else None
                except (ValueError, TypeError):
                    o = None
                try:
                    j = float(juri_raw) if juri_raw != '' and juri_raw is not None else None
                except (ValueError, TypeError):
                    j = None

                if o is not None and j is not None:
                    avg_tp = round((o + j) / 2.0, 2)
                elif o is not None:
                    avg_tp = o
                elif j is not None:
                    avg_tp = j
                else:
                    avg_tp = None

                pred_tp, ket_tp = get_koku_predikat_and_ket(avg_tp) if avg_tp is not None else ('', '')

                tp_row_data.append({
                    'nomor': i,
                    'obs': f"{o:.2f}".rstrip('0').rstrip('.') if o is not None else '',
                    'juri': f"{j:.2f}".rstrip('0').rstrip('.') if j is not None else '',
                    'avg': f"{avg_tp:.2f}".rstrip('0').rstrip('.') if avg_tp is not None else '',
                    'predikat': pred_tp,
                    'ket': ket_tp,
                })
                if avg_tp is not None:
                    tp_data_for_desc.append({
                        'nomor': i,
                        'avg': avg_tp,
                        'predikat': pred_tp,
                        'ket': ket_tp,
                        'deskripsi': tp_descriptions.get(i, f"aspek ke-{i}")
                    })

            if k and k.deskripsi:
                desk_val = k.deskripsi
            elif tp_data_for_desc:
                desk_val = generate_kokurikuler_combined_deskripsi(tp_data_for_desc)
            else:
                desk_val = ""

            rata_val = ""
            if k and k.nilai_angka > 0:
                val_k = k.nilai_angka
                if val_k > 4.0:
                    val_k = round(val_k / 25.0, 2)
                rata_val = f"{val_k:.2f}".rstrip('0').rstrip('.')

            row_data.append({
                'anggota': a,
                'tp_row_data': tp_row_data,
                'scores': {i: scores.get(str(i), '') for i in range(1, 8)},
                'rata_rata': rata_val,
                'predikat': k.predikat if k else 'A',
                'deskripsi': desk_val,
            })

    context = {
        'selected_kelas': selected_kelas,
        'kelas_list': kelas_list,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
        'tp_range': tp_range,
        'tp_descriptions': tp_descriptions,
        'tp_descriptions_json': json.dumps(tp_descriptions),
    }
    return render(request, 'penilaian/kokurikuler_matrix.html', context)


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def ekskul_matrix_view(request, kelas_id=None):
    """
    Submenu Tugas Khusus Wali Kelas:
    Matriks Input Ekstrakurikuler per rombel kelas.
    Tabel berkolom mirip Matriks Nilai Rapor:
    Paling kiri: No & Nama Siswa.
    Lalu 6 kelompok kolom Ekstrakurikuler 1 s/d 6 (Kegiatan, Predikat, Keterangan).
    Wali kelas dapat menyunting langsung secara manual.
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()

    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
    if pendidik and pendidik.role == 'WALI_KELAS':
        kelas_asuhan = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).first() or pendidik.kelas_asuhan.first()
        target_kelas_id = kelas_asuhan.id if kelas_asuhan else None
        kelas_list = Kelas.objects.filter(id=kelas_asuhan.id) if kelas_asuhan else Kelas.objects.none()
    else:
        target_kelas_id = kelas_id or request.GET.get('kelas') or (kelas_list.first().id if kelas_list.exists() else None)

    selected_kelas = get_object_or_404(Kelas, id=target_kelas_id) if target_kelas_id else None

    if pendidik and pendidik.role == 'WALI_KELAS' and selected_kelas:
        if selected_kelas.wali_kelas_id != pendidik.id and not user.is_superuser:
            messages.error(request, "Anda hanya berwenang mengelola data kelas yang Anda ampu sebagai wali kelas.")
            return redirect('dashboard')

    row_data = []
    if selected_kelas:
        anggota_list = AnggotaKelas.objects.filter(kelas=selected_kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')
        
        ekskul_qs = EkstrakurikulerNilai.objects.filter(
            anggota_kelas__in=anggota_list,
            semester=sem_aktif
        )
        ekskul_dict = {(e.anggota_kelas_id, e.urutan): e for e in ekskul_qs}

        if request.method == 'POST':
            for a in anggota_list:
                for i in range(1, 7):
                    keg = request.POST.get(f"murid_{a.id}_ekskul_{i}_kegiatan", "").strip()
                    pred = request.POST.get(f"murid_{a.id}_ekskul_{i}_predikat", "A").strip()
                    ket = request.POST.get(f"murid_{a.id}_ekskul_{i}_keterangan", "").strip()

                    if keg:
                        EkstrakurikulerNilai.objects.update_or_create(
                            anggota_kelas=a,
                            semester=sem_aktif,
                            urutan=i,
                            defaults={
                                'kegiatan': keg,
                                'predikat': pred,
                                'keterangan': ket
                            }
                        )
                    else:
                        EkstrakurikulerNilai.objects.filter(
                            anggota_kelas=a,
                            semester=sem_aktif,
                            urutan=i
                        ).delete()

            messages.success(request, f"Alhamdulillaah, data penilaian Ekstrakurikuler kelas {selected_kelas.nama} berhasil disimpan.")
            return redirect(f"{request.path}?kelas={selected_kelas.id}")

        for a in anggota_list:
            slots = []
            for i in range(1, 7):
                item = ekskul_dict.get((a.id, i))
                slots.append({
                    'urutan': i,
                    'kegiatan': item.kegiatan if item else '',
                    'predikat': item.predikat if item else 'A',
                    'keterangan': item.keterangan if item else '',
                })
            row_data.append({
                'anggota': a,
                'slots': slots,
            })

    context = {
        'selected_kelas': selected_kelas,
        'kelas_list': kelas_list,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
        'slot_range': list(range(1, 7)),
    }
    return render(request, 'penilaian/ekskul_matrix.html', context)


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def prestasi_matrix_view(request, kelas_id=None):
    """
    Submenu Tugas Khusus Wali Kelas:
    Matriks Input Prestasi & Penghargaan Murid per rombel kelas (Halaman 5 Rapor).
    Tabel spreadsheet interaktif:
    Paling kiri: No & Nama Siswa.
    Lalu 6 kelompok kolom Prestasi 1 s/d 6 (Jenis Prestasi, Keterangan).
    Wali kelas dapat menyunting langsung secara manual.
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()

    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()
    if pendidik and pendidik.role == 'WALI_KELAS':
        kelas_asuhan = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).first() or pendidik.kelas_asuhan.first()
        target_kelas_id = kelas_asuhan.id if kelas_asuhan else None
        kelas_list = Kelas.objects.filter(id=kelas_asuhan.id) if kelas_asuhan else Kelas.objects.none()
    else:
        target_kelas_id = kelas_id or request.GET.get('kelas') or (kelas_list.first().id if kelas_list.exists() else None)

    selected_kelas = get_object_or_404(Kelas, id=target_kelas_id) if target_kelas_id else None

    if pendidik and pendidik.role == 'WALI_KELAS' and selected_kelas:
        if selected_kelas.wali_kelas_id != pendidik.id and not user.is_superuser:
            messages.error(request, "Anda hanya berwenang mengelola data kelas yang Anda ampu sebagai wali kelas.")
            return redirect('dashboard')

    row_data = []
    if selected_kelas:
        anggota_list = AnggotaKelas.objects.filter(kelas=selected_kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')
        
        prestasi_qs = PrestasiMurid.objects.filter(
            anggota_kelas__in=anggota_list,
            semester=sem_aktif
        )
        prestasi_dict = {(p.anggota_kelas_id, p.urutan): p for p in prestasi_qs}

        if request.method == 'POST':
            for a in anggota_list:
                for i in range(1, 7):
                    jenis = request.POST.get(f"murid_{a.id}_prestasi_{i}_jenis", "").strip()
                    ket = request.POST.get(f"murid_{a.id}_prestasi_{i}_keterangan", "").strip()

                    if jenis:
                        PrestasiMurid.objects.update_or_create(
                            anggota_kelas=a,
                            semester=sem_aktif,
                            urutan=i,
                            defaults={
                                'jenis_prestasi': jenis,
                                'keterangan': ket
                            }
                        )
                    else:
                        PrestasiMurid.objects.filter(
                            anggota_kelas=a,
                            semester=sem_aktif,
                            urutan=i
                        ).delete()

            messages.success(request, f"Data Prestasi Murid Kelas {selected_kelas.nama} berhasil disimpan.")
            return redirect('prestasi_matrix_kelas', kelas_id=selected_kelas.id)

        for a in anggota_list:
            slots = []
            for i in range(1, 7):
                item = prestasi_dict.get((a.id, i))
                slots.append({
                    'urutan': i,
                    'jenis': item.jenis_prestasi if item else '',
                    'keterangan': item.keterangan if item else '',
                })
            row_data.append({
                'anggota': a,
                'slots': slots,
            })

    context = {
        'selected_kelas': selected_kelas,
        'kelas_list': kelas_list,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
        'slot_range': list(range(1, 7)),
    }
    return render(request, 'penilaian/prestasi_matrix.html', context)



@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def ekskul_prestasi_kelas_view(request, kelas_id):
    """
    Submenu Tugas Khusus Wali Kelas:
    Pengelolaan Ekstrakurikuler (Hal 4) & Prestasi Murid (Hal 5) per Rombel Kelas.
    """
    kelas = get_object_or_404(Kelas, id=kelas_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()

    user_role = getattr(request.user, 'role', 'GURU_MAPEL')
    if user_role == 'WALI_KELAS' and hasattr(request.user, 'profil_pendidik'):
        if kelas.wali_kelas_id != request.user.profil_pendidik.id:
            messages.error(request, "Anda hanya berwenang mengelola data kelas yang Anda ampu sebagai wali kelas.")
            return redirect('dashboard')

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    from collections import defaultdict
    ekskul_count = defaultdict(int)
    for e in EkstrakurikulerNilai.objects.filter(anggota_kelas__in=anggota_list, semester=sem_aktif):
        ekskul_count[e.anggota_kelas_id] += 1

    prestasi_count = defaultdict(int)
    for p in PrestasiMurid.objects.filter(anggota_kelas__in=anggota_list, semester=sem_aktif):
        prestasi_count[p.anggota_kelas_id] += 1

    row_data = []
    for a in anggota_list:
        row_data.append({
            'anggota': a,
            'ekskul_count': ekskul_count[a.id],
            'prestasi_count': prestasi_count[a.id],
        })

    kelas_list = Kelas.objects.all().order_by('tingkat', 'nama')

    context = {
        'kelas': kelas,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
        'kelas_list': kelas_list,
        'user_role': user_role,
    }
    return render(request, 'penilaian/ekskul_prestasi_kelas.html', context)


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def ekskul_prestasi_input_view(request, anggota_id):
    """
    Formulir input Ekstrakurikuler (maks 6 baris) & Prestasi (maks 6 baris) per murid.
    Sesuai layout cetak rapor Halaman 4 dan Halaman 5.
    """
    anggota = get_object_or_404(AnggotaKelas.objects.select_related('murid', 'kelas'), id=anggota_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()

    user_role = getattr(request.user, 'role', 'GURU_MAPEL')
    if user_role == 'WALI_KELAS' and hasattr(request.user, 'profil_pendidik'):
        if anggota.kelas.wali_kelas_id != request.user.profil_pendidik.id:
            messages.error(request, "Anda hanya berwenang mengelola data kelas yang Anda ampu sebagai wali kelas.")
            return redirect('dashboard')

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
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
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
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def catatan_wali_input_view(request, kelas_id=None):
    """
    Formulir input Catatan Naratif Wali Kelas (Halaman 4 cetak rapor).
    """
    user = request.user
    pendidik = getattr(user, 'profil_pendidik', None)
    is_admin = user.is_superuser or (pendidik and pendidik.role in ['SUPERADMIN', 'KURIKULUM'])

    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()

    if is_admin:
        kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif).order_by('tingkat', 'nama') if ta_aktif else Kelas.objects.all().order_by('tingkat', 'nama')
    elif pendidik and pendidik.role == 'WALI_KELAS':
        kelas_list = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).order_by('tingkat', 'nama') if ta_aktif else pendidik.kelas_asuhan.all().order_by('tingkat', 'nama')
    else:
        kelas_list = Kelas.objects.none()

    target_param = request.GET.get('kelas')
    if target_param:
        try:
            target_id = int(target_param)
            if target_id != kelas_id:
                return redirect('catatan_wali_input', kelas_id=target_id)
        except (ValueError, TypeError):
            pass

    if not kelas_id:
        if kelas_list.exists():
            return redirect('catatan_wali_input', kelas_id=kelas_list.first().id)
        else:
            messages.error(request, "Belum ada rombel kelas yang terdaftar.")
            return redirect('dashboard')

    kelas = get_object_or_404(Kelas, id=kelas_id)

    if not is_admin and pendidik and pendidik.role == 'WALI_KELAS':
        if kelas.wali_kelas_id != pendidik.id:
            messages.error(request, "Anda hanya berwenang mengakses catatan kelas asuhan Anda.")
            return redirect('dashboard')

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
        'kelas_list': kelas_list,
        'sem_aktif': sem_aktif,
        'row_data': row_data,
        'is_admin': is_admin,
    }
    return render(request, 'penilaian/catatan_wali_input.html', context)
