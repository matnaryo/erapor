from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.core.decorators import role_required
from apps.master_akademik.models import Kelas, AnggotaKelas, Semester, TahunAjaran
from apps.penilaian.models import NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
from .ollama_client import generate_wali_kelas_note, OLLAMA_MODEL

def collect_student_grade_profile(anggota, sem_aktif):
    """
    Membaca dan merangkum seluruh data nilai 11 mata pelajaran, rata-rata,
    mupel unggul, aspek yang perlu ditingkatkan, pembiasaan ibadah, dan presensi murid.
    """
    nilai_qs = NilaiAkhir.objects.filter(
        anggota_kelas=anggota,
        pembelajaran_kelas__semester=sem_aktif
    ).select_related('pembelajaran_kelas__mata_pelajaran').order_by('pembelajaran_kelas__mata_pelajaran__urutan')

    daftar_nilai = []
    nilai_values = []
    mupel_unggul = []
    mupel_perlu = []

    for n in nilai_qs:
        mupel_nama = n.pembelajaran_kelas.mata_pelajaran.nama
        if n.nilai_angka is not None:
            val = float(n.nilai_angka)
            nilai_values.append(val)
            daftar_nilai.append({
                'nama': mupel_nama,
                'nilai': val,
                'predikat': n.predikat,
                'tertinggi': n.capaian_tertinggi,
                'perlu': n.capaian_perlu_bimbingan
            })
            if val >= 88:
                mupel_unggul.append(f"{mupel_nama} ({val:.0f})")
            elif val < 80 or (n.capaian_perlu_bimbingan and n.capaian_perlu_bimbingan != '-'):
                mupel_perlu.append(f"{mupel_nama} ({val:.0f})")

    # Jika belum ada yang >= 88, ambil 2 mupel teratas
    if not mupel_unggul and daftar_nilai:
        sorted_top = sorted(daftar_nilai, key=lambda x: x['nilai'], reverse=True)[:2]
        mupel_unggul = [f"{x['nama']} ({x['nilai']:.0f})" for x in sorted_top]

    rata_rata = sum(nilai_values) / len(nilai_values) if nilai_values else 0.0

    koku = KokurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem_aktif).first()
    koku_desc = koku.deskripsi if koku else ""

    prestasi_qs = PrestasiMurid.objects.filter(anggota_kelas=anggota, semester=sem_aktif)
    prestasi_desc = ", ".join([p.jenis_prestasi for p in prestasi_qs]) if prestasi_qs.exists() else ""

    ekskul_qs = EkstrakurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem_aktif)
    ekskul_desc = ", ".join([f"{e.kegiatan} ({e.predikat})" for e in ekskul_qs]) if ekskul_qs.exists() else ""

    absen = Ketidakhadiran.objects.filter(anggota_kelas=anggota, semester=sem_aktif).first()
    sakit = absen.sakit if absen else 0
    izin = absen.izin if absen else 0
    alpa = absen.tanpa_keterangan if absen else 0

    return {
        'daftar_nilai': daftar_nilai,
        'rata_rata': rata_rata,
        'mupel_unggul': mupel_unggul,
        'mupel_perlu_bimbingan': mupel_perlu,
        'kokurikuler': koku_desc,
        'prestasi': prestasi_desc,
        'ekskul': ekskul_desc,
        'sakit': sakit,
        'izin': izin,
        'alpa': alpa,
    }


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def ai_generate_notes_kelas_view(request, kelas_id=None):
    """
    Dashboard interaktif Asisten AI untuk Catatan Perkembangan Murid (SDIT Luqman Al Hakim Sleman).
    Membaca nilai lengkap anak menggunakan model Ollama qwen2.5:1.5b, merumuskan ringkasan evaluasi,
    serta memberikan saran konkret perkembangan murid.
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

    # Perpindahan rombel jika ada parameter GET ?kelas=
    target_param = request.GET.get('kelas')
    if target_param:
        try:
            target_id = int(target_param)
            if target_id != kelas_id:
                return redirect('ai_generate_notes_kelas', kelas_id=target_id)
        except (ValueError, TypeError):
            pass

    if not kelas_id:
        if kelas_list.exists():
            return redirect('ai_generate_notes_kelas', kelas_id=kelas_list.first().id)
        else:
            messages.error(request, "Belum ada rombel kelas yang terdaftar.")
            return redirect('dashboard')

    kelas = get_object_or_404(Kelas, id=kelas_id)

    # Validasi wewenang wali kelas jika bukan superadmin / kurikulum
    if not is_admin and pendidik and pendidik.role == 'WALI_KELAS':
        if kelas.wali_kelas_id != pendidik.id:
            messages.error(request, "Anda hanya berwenang mengakses catatan perkembangan murid untuk kelas asuhan Anda.")
            return redirect('dashboard')

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')

    catatan_dict = {
        c.anggota_kelas_id: c for c in CatatanWaliKelas.objects.filter(
            semester=sem_aktif,
            anggota_kelas__in=anggota_list
        )
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate_single':
            # Generate untuk 1 murid tertentu
            target_anggota_id = request.POST.get('anggota_id')
            target_anggota = get_object_or_404(AnggotaKelas, id=target_anggota_id, kelas=kelas)
            profile = collect_student_grade_profile(target_anggota, sem_aktif)

            draft_text, is_ai, prompt_used = generate_wali_kelas_note(
                nama_murid=target_anggota.murid.nama_lengkap,
                daftar_nilai=profile['daftar_nilai'],
                rata_rata=profile['rata_rata'],
                mupel_unggul=profile['mupel_unggul'],
                mupel_perlu_bimbingan=profile['mupel_perlu_bimbingan'],
                kokurikuler=profile['kokurikuler'],
                prestasi=profile['prestasi'],
                ekskul=profile['ekskul'],
                sakit=profile['sakit'],
                izin=profile['izin'],
                alpa=profile['alpa']
            )

            CatatanWaliKelas.objects.update_or_create(
                anggota_kelas=target_anggota,
                semester=sem_aktif,
                defaults={
                    'catatan': draft_text,
                    'is_generated_by_ai': is_ai,
                    'ai_prompt_history': prompt_used
                }
            )
            messages.success(request, f"Draft Catatan Perkembangan untuk '{target_anggota.murid.nama_lengkap}' berhasil digenerate oleh {OLLAMA_MODEL}.")
            return redirect('ai_generate_notes_kelas', kelas_id=kelas.id)

        elif action == 'generate_all':
            # Generate draft untuk seluruh murid di kelas
            success_count = 0
            for anggota in anggota_list:
                profile = collect_student_grade_profile(anggota, sem_aktif)

                draft_text, is_ai, prompt_used = generate_wali_kelas_note(
                    nama_murid=anggota.murid.nama_lengkap,
                    daftar_nilai=profile['daftar_nilai'],
                    rata_rata=profile['rata_rata'],
                    mupel_unggul=profile['mupel_unggul'],
                    mupel_perlu_bimbingan=profile['mupel_perlu_bimbingan'],
                    kokurikuler=profile['kokurikuler'],
                    prestasi=profile['prestasi'],
                    ekskul=profile['ekskul'],
                    sakit=profile['sakit'],
                    izin=profile['izin'],
                    alpa=profile['alpa']
                )

                CatatanWaliKelas.objects.update_or_create(
                    anggota_kelas=anggota,
                    semester=sem_aktif,
                    defaults={
                        'catatan': draft_text,
                        'is_generated_by_ai': is_ai,
                        'ai_prompt_history': prompt_used
                    }
                )
                success_count += 1

            messages.success(request, f"Alhamdulillaah, berhasil men-generate draft Catatan Perkembangan untuk {success_count} murid menggunakan model {OLLAMA_MODEL}.")
            return redirect('ai_generate_notes_kelas', kelas_id=kelas.id)

        elif action == 'save_all':
            # Simpan seluruh perubahan / suntingan wali kelas
            for anggota in anggota_list:
                catatan = request.POST.get(f"catatan_{anggota.id}", "").strip()
                if catatan:
                    CatatanWaliKelas.objects.update_or_create(
                        anggota_kelas=anggota,
                        semester=sem_aktif,
                        defaults={'catatan': catatan}
                    )
            messages.success(request, f"Seluruh Catatan Wali Kelas untuk kelas {kelas.nama} berhasil disimpan ke pangkalan data.")
            return redirect('ai_generate_notes_kelas', kelas_id=kelas.id)

    # Siapkan data lengkap untuk view
    murid_data = []
    for anggota in anggota_list:
        cat = catatan_dict.get(anggota.id)
        profile = collect_student_grade_profile(anggota, sem_aktif)
        murid_data.append({
            'anggota': anggota,
            'catatan': cat.catatan if cat else '',
            'is_ai': cat.is_generated_by_ai if cat else False,
            'updated_at': cat.updated_at if cat else None,
            'profile': profile,
        })

    context = {
        'kelas': kelas,
        'kelas_list': kelas_list,
        'sem_aktif': sem_aktif,
        'murid_data': murid_data,
        'total_murid': len(anggota_list),
        'model_name': OLLAMA_MODEL,
        'is_admin': is_admin,
    }
    return render(request, 'ai_assistant/generate_notes.html', context)
