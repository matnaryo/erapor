from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.master_akademik.models import Kelas, AnggotaKelas, Semester
from apps.penilaian.models import NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
from .ollama_client import generate_wali_kelas_note

@login_required(login_url='login')
def ai_generate_notes_kelas_view(request, kelas_id):
    """
    Dashboard interaktif Asisten AI untuk Catatan Wali Kelas (SDIT Luqman Al Hakim Sleman).
    Mendukung generate per murid, generate seluruh kelas (bulk), penyuntingan, dan persetujuan.
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

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate_all':
            # Generate draft untuk seluruh murid di kelas
            success_count = 0
            for anggota in anggota_list:
                # Kumpulkan data murid
                nilai_qs = NilaiAkhir.objects.filter(anggota_kelas=anggota, pembelajaran_kelas__semester=sem_aktif)
                top_nilai = nilai_qs.order_by('-nilai_angka').first()
                summary_nilai = f"Nilai terbaik pada mata pelajaran {top_nilai.pembelajaran_kelas.mata_pelajaran.nama} ({top_nilai.nilai_angka})" if top_nilai else ""

                koku = KokurikulerNilai.objects.filter(anggota_kelas=anggota, semester=sem_aktif).first()
                koku_desc = koku.deskripsi if koku else ""

                prestasi_qs = PrestasiMurid.objects.filter(anggota_kelas=anggota, semester=sem_aktif)
                prestasi_desc = ", ".join([p.jenis_prestasi for p in prestasi_qs]) if prestasi_qs.exists() else ""

                absen = Ketidakhadiran.objects.filter(anggota_kelas=anggota, semester=sem_aktif).first()
                sakit = absen.sakit if absen else 0
                izin = absen.izin if absen else 0
                alpa = absen.tanpa_keterangan if absen else 0

                draft_text, is_ai, prompt_used = generate_wali_kelas_note(
                    nama_murid=anggota.murid.nama_lengkap,
                    nilai_summary=summary_nilai,
                    kokurikuler=koku_desc,
                    prestasi=prestasi_desc,
                    sakit=sakit,
                    izin=izin,
                    alpa=alpa
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

            messages.success(request, f"Berhasil men-generate draft Catatan Wali Kelas untuk {success_count} murid menggunakan Ollama qwen2.5-coder:3b.")
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
            messages.success(request, f"Seluruh Catatan Wali Kelas untuk kelas {kelas.nama} berhasil disimpan.")
            return redirect('ai_generate_notes_kelas', kelas_id=kelas.id)

    # Siapkan data view
    murid_data = []
    for anggota in anggota_list:
        cat = catatan_dict.get(anggota.id)
        murid_data.append({
            'anggota': anggota,
            'catatan': cat.catatan if cat else '',
            'is_ai': cat.is_generated_by_ai if cat else False,
            'updated_at': cat.updated_at if cat else None,
        })

    context = {
        'kelas': kelas,
        'sem_aktif': sem_aktif,
        'murid_data': murid_data,
        'total_murid': len(anggota_list),
    }
    return render(request, 'ai_assistant/generate_notes.html', context)
