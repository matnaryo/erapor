import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate")
# Model Qwen Instruct lokal yang tersedia di komputer pengguna (qwen2.5:1.5b ringan & responsif)
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')

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
    timeout=120
):
    """
    Menghasilkan draft narasi Catatan Wali Kelas yang membaca nilai akademik lengkap murid,
    merangkum perkembangan belajar dan adab, serta memberikan saran konkret tindak lanjut,
    menggunakan model Local AI Ollama 'qwen3:4b-instruct'.
    Menyediakan fallback cerdas otomatis berbasis data riil jika layanan offline/timeout.
    """
    first_name = nama_murid.split()[0]
    
    # Siapkan rekapitulasi data nilai ringkas dan padat untuk efisiensi CPU inference Ollama
    nilai_lines = []
    if daftar_nilai:
        for n in daftar_nilai:
            baris = f"- {n.get('nama')}: {n.get('nilai')}"
            perlu_text = n.get('perlu') or ""
            if "perlu bimbingan" in perlu_text.lower():
                clean_perlu = perlu_text.replace("Murid perlu bimbingan dalam ", "").strip()
                baris += f" (Perlu penguatan: {clean_perlu})"
            nilai_lines.append(baris)
    teks_daftar_nilai = "\n".join(nilai_lines) if nilai_lines else "- Nilai tuntas di seluruh mata pelajaran."

    unggul_str = ", ".join(mupel_unggul) if mupel_unggul else "sebagian besar mata pelajaran"
    bimbingan_str = ", ".join(mupel_perlu_bimbingan) if mupel_perlu_bimbingan else ""

    system_prompt = (
        "Anda adalah Wali Kelas sekaligus Asisten AI Resmi di SDIT Luqman Al Hakim Sleman (e-Rapor eLHaEs). "
        "Tugas utama Anda adalah menyusun 1 paragraf narasi Catatan Wali Kelas untuk buku rapor semester. "
        "Ketentuan penulisan narasi:\n"
        f"1. Selalu gunakan panggilan akrab 'ananda {first_name}' (bukan nama panjang lengkap murid).\n"
        "2. Membaca capaian nilai anak dan memberikan ringkasan perkembangan belajar serta pembiasaan ibadah/adab murid.\n"
        "3. Memberikan saran konkret/rekomendasi tindak lanjut bagi orang tua dan murid terkait materi/mata pelajaran yang perlu ditingkatkan di rumah.\n"
        "4. Gaya bahasa: Sangat santun, apresiatif, mendidik, hangat, bernuansa Islami khas SDIT.\n"
        "5. Format penulisan: Tepat 1 paragraf utuh (4 sampai 5 kalimat padat dan ringkas, total 60-85 kata), tanpa bullet points (* atau -), "
        "diawali rasa syukur ('Alhamdulillaah...'), dan diakhiri doa keberkahan ('Barakallahu fiik').\n"
        "6. Hanya keluarkan teks catatan rapor langsung tanpa salam pembuka surat atau kata pengantar."
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
                    "num_predict": 260,
                    "num_ctx": 2048,
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
                # Jika terpotong di tengah kalimat terakhir akibat batas token, rapikan ke akhir kalimat terdekat
                if not output_text.endswith(('.', '!', '?')) and '.' in output_text:
                    output_text = output_text.rsplit('.', 1)[0] + '.'
                if 'Barakallahu fiik' not in output_text:
                    output_text += ' Barakallahu fiik.'
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


def generate_capaian_kompetensi_ai(
    nama_murid,
    mupel_nama,
    nilai_akhir,
    predikat,
    max_desc,
    min_desc="",
    timeout=30
):
    """
    Menghasilkan narasi capaian kompetensi tertinggi dan yang perlu bimbingan
    yang disempurnakan oleh Model Qwen Instruct lokal untuk mata pelajaran tertentu.
    Jika Ollama offline/timeout, langsung mengembalikan narasi terstruktur baku.
    """
    first_name = nama_murid.split()[0]
    clean_max = max_desc.strip()
    clean_min = min_desc.strip() if min_desc else ""

    if predikat == 'A':
        def_tertinggi = f"Murid menunjukkan penguasaan yang sangat baik dalam {clean_max}."
    elif predikat == 'B':
        def_tertinggi = f"Murid menunjukkan penguasaan yang baik dalam {clean_max}."
    else:
        def_tertinggi = f"Murid cukup mampu dalam {clean_max}."

    if clean_min:
        def_perlu = f"Murid perlu bimbingan dan pendampingan dalam {clean_min}."
    else:
        def_perlu = ""

    system_prompt = (
        "Anda adalah Guru dan Asisten AI Resmi di SDIT Luqman Al Hakim Sleman. "
        "Tugas Anda adalah merumuskan dua kalimat capaian rapor Kurikulum Merdeka untuk satu mata pelajaran:\n"
        "1. Capaian Tertinggi: Frasa narasi capaian materi terbaik yang dikuasai murid.\n"
        "2. Capaian Perlu Bimbingan: Frasa narasi materi yang perlu bimbingan/ditingkatkan.\n"
        "Format respon WAJIB berupa JSON persis seperti ini:\n"
        '{"tertinggi": "...", "perlu": "..."}\n'
        "Gunakan bahasa Indonesia baku, santun, dan mendidik. Tanpa kata pengantar tambahan."
    )

    user_prompt = (
        f"Nama Murid: {first_name}\n"
        f"Mata Pelajaran: {mupel_nama}\n"
        f"Nilai Akhir: {nilai_akhir} (Predikat {predikat})\n"
        f"Materi Tertinggi yang Dikuasai: {clean_max}\n"
        f"Materi yang Perlu Penguatan: {clean_min or 'Tidak ada materi di bawah KKTP'}\n"
        "Buatkan capaian tertinggi dan perlu bimbingan dalam JSON:"
    )

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "num_predict": 150,
                    "num_ctx": 2048,
                }
            },
            timeout=timeout
        )
        if response.status_code == 200:
            result = response.json()
            output = result.get("response", "").strip()
            if '{' in output and '}' in output:
                json_part = output[output.find('{'):output.rfind('}')+1]
                data = json.loads(json_part)
                tertinggi = data.get('tertinggi', def_tertinggi).strip()
                perlu = data.get('perlu', def_perlu).strip()
                return tertinggi, perlu, True
    except Exception as e:
        logger.warning(f"Ollama AI Capaian ({OLLAMA_MODEL}) failed: {e}. Menggunakan fallback baku.")

    return def_tertinggi, def_perlu, False
