import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/api/generate')
# Model Qwen Instruct lokal yang tersedia di komputer pengguna
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:4b-instruct')

def generate_wali_kelas_note(
    nama_murid,
    daftar_nilai=None,
    rata_rata=0.0,
    mupel_unggul=None,
    mupel_perlu_bimbingan=None,
    kokurikuler="",
    prestasi="",
    ekskul="",
    sakit=0,
    izin=0,
    alpa=0,
    timeout=90
):
    """
    Menghasilkan draft narasi Catatan Wali Kelas yang membaca nilai akademik lengkap murid,
    merangkum perkembangan belajar dan adab, serta memberikan saran konkret tindak lanjut,
    menggunakan model Local AI Ollama 'qwen3:4b-instruct'.
    Menyediakan fallback cerdas otomatis berbasis data riil jika layanan offline/timeout.
    """
    first_name = nama_murid.split()[0]
    
    # Siapkan rekapitulasi data nilai untuk dibaca oleh model
    nilai_lines = []
    if daftar_nilai:
        for n in daftar_nilai:
            baris = f"- {n.get('nama')}: {n.get('nilai')}"
            if n.get('perlu'):
                baris += f" (Perlu penguatan: {n.get('perlu')})"
            nilai_lines.append(baris)
    teks_daftar_nilai = "\n".join(nilai_lines) if nilai_lines else "- Nilai tuntas di seluruh mata pelajaran."

    unggul_str = ", ".join(mupel_unggul) if mupel_unggul else "sebagian besar mata pelajaran"
    bimbingan_str = ", ".join(mupel_perlu_bimbingan) if mupel_perlu_bimbingan else ""

    system_prompt = (
        "Anda adalah Wali Kelas sekaligus Asisten AI Resmi di SDIT Luqman Al Hakim Sleman (e-Rapor eLHaEs). "
        "Tugas utama Anda adalah MEMBACA data nilai akademik murid, menganalisis kekuatan dan aspek yang perlu bimbingan, "
        "lalu menyusun 1 paragraf narasi Catatan Wali Kelas untuk buku rapor semester. "
        "Ketentuan penulisan narasi:\n"
        "1. Membaca capaian nilai anak dan memberikan ringkasan perkembangan belajar serta pembiasaan ibadah/adab murid.\n"
        "2. Memberikan saran konkret/rekomendasi tindak lanjut bagi orang tua dan murid terkait materi atau mata pelajaran yang perlu ditingkatkan di rumah.\n"
        "3. Gaya bahasa: Sangat santun, apresiatif, mendidik, hangat, bernuansa Islami khas SDIT.\n"
        "4. Format penulisan: Tepat 1 paragraf utuh (4 sampai 5 kalimat padat), tanpa bullet points (* atau -), "
        "diawali rasa syukur/apresiasi (seperti 'Alhamdulillaah...'), dan diakhiri doa keberkahan ('Barakallahu fiik').\n"
        "5. Hanya keluarkan teks catatan rapor langsung tanpa salam pembuka surat atau kata pengantar."
    )

    user_prompt = f"""Berikut adalah data capaian nilai dan profil murid:
Nama Murid: {nama_murid}
Rata-rata Nilai Akademik: {rata_rata:.1f}
Mata Pelajaran Unggulan: {unggul_str}
Mata Pelajaran yang Perlu Peningkatan: {bimbingan_str or 'Tidak ada nilai di bawah batas KKTP'}

Daftar Nilai Lengkap:
{teks_daftar_nilai}

Kokurikuler (Ibadah & Karakter): {kokurikuler or 'Tertib sholat dhuha dan sholat berjamaah.'}
Prestasi & Ekstrakurikuler: {prestasi or ekskul or 'Aktif mengikuti kegiatan sekolah.'}
Presensi: Sakit {sakit} hari, Izin {izin} hari, Alpa {alpa} hari.

Tolong baca nilai-nilai di atas, lalu buatkan 1 paragraf narasi Catatan Wali Kelas yang merangkum perkembangan ananda dan memberikan saran konkret bagi tindak lanjut belajarnya di rumah:"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.65,
                    "top_p": 0.9,
                    "max_tokens": 300,
                }
            },
            timeout=timeout
        )

        if response.status_code == 200:
            result = response.json()
            output_text = result.get("response", "").strip()
            # Pembersihan tanda kutip atau formatting markdown berlebih
            if output_text.startswith('```') and output_text.endswith('```'):
                lines = output_text.split('\n')
                output_text = "\n".join(lines[1:-1]).strip()
            if output_text.startswith('"') and output_text.endswith('"'):
                output_text = output_text[1:-1].strip()

            if output_text and len(output_text) > 30:
                return output_text, True, user_prompt

    except Exception as e:
        logger.warning(f"Ollama local AI request ({OLLAMA_MODEL}) failed: {e}. Menggunakan fallback cerdas berbasis data riil.")

    # Cerdas berbasis data riil murid jika server AI sedang timeout/offline
    saran_spesifik = f"khususnya penguatan pada {bimbingan_str}" if bimbingan_str else "khususnya ketelitian berhitung dan literasi membaca"
    fallback_text = (
        f"Alhamdulillaah, ananda {first_name} menunjukkan perkembangan belajar yang sangat baik di semester ini "
        f"dengan rata-rata nilai {rata_rata:.1f}, terutama unggul pada mata pelajaran {unggul_str}, "
        f"serta istiqomah dalam pembiasaan sholat dhuha dan sholat berjamaah. "
        f"Sebagai saran tindak lanjut, ananda diharapkan terus meluangkan waktu latihan rutin di rumah, {saran_spesifik}, "
        f"didampingi pengulangan muraja'ah tahfidz Al-Qur'an bersama keluarga. "
        f"Semoga Allah Subhanahu wa Ta'ala senantiasa melimpahkan taufiq dan memelihara ananda menjadi generasi sholih, cerdas, serta berakhlak mulia. "
        f"Barakallahu fiik."
    )
    return fallback_text, False, user_prompt
