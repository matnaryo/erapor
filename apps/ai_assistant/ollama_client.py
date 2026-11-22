import os
import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate")
# Model Qwen lokal yang aktif digunakan (default: qwen2.5:1.5b)
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:1.5b')
if not OLLAMA_MODEL or 'qwen3' in OLLAMA_MODEL.lower():
    OLLAMA_MODEL = 'qwen2.5:1.5b'

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
    menggunakan model Local AI Ollama qwen2.5:1.5b.
    Menyediakan fallback cerdas otomatis berbasis data riil jika layanan offline/timeout.
    """
    first_name = nama_murid.split()[0].title()
    mupel_unggul = mupel_unggul or []
    mupel_perlu_bimbingan = mupel_perlu_bimbingan or []
    unggul_str = ", ".join(mupel_unggul) if mupel_unggul else "sebagian besar mata pelajaran"
    bimbingan_str = ", ".join(mupel_perlu_bimbingan) if mupel_perlu_bimbingan else ""
    
    # Ekstrak poin penguatan materi yang spesifik membutuhkan bimbingan
    perlu_poin = []
    if daftar_nilai:
        for n in daftar_nilai:
            p = n.get('perlu') or ''
            if 'perlu bimbingan' in p.lower():
                clean = p.replace('Murid perlu bimbingan dalam ', '').strip().rstrip('.')
                perlu_poin.append(f"{n.get('nama')} ({clean})")
    
    perlu_ringkas = ", ".join(perlu_poin[:2]) if perlu_poin else (bimbingan_str or "seluruh materi telah tuntas dengan baik")
    unggul_ringkas = ", ".join(mupel_unggul[:2]) if mupel_unggul else "sebagian besar mata pelajaran"

    system_prompt = (
        "Anda adalah Asisten Wali Kelas SDIT Luqman Al Hakim Sleman (e-Rapor eLHaEs). "
        "Tugas Anda menyusun 1 paragraf narasi mengalir yang santun dan bernuansa Islami untuk buku rapor semester. "
        "Narasi harus memuat apresiasi nilai unggulan, pujian ibadah/adab, saran konkret penguatan materi belajar di rumah, "
        "diawali ucapan 'Alhamdulillaah' dan diakhiri doa 'Barakallahu fiik.'. "
        "Dilarang menggunakan bullet point, nomor urut, atau kata pengantar."
    )

    user_prompt = f"""Data capaian ananda {nama_murid}:
- Rata-rata nilai: {rata_rata:.1f}
- Nilai unggulan: {unggul_ringkas}
- Perlu bimbingan di rumah: {perlu_ringkas}
- Ibadah & Karakter: {kokurikuler or 'Tertib sholat dhuha dan sholat berjamaah.'}
- Ekstrakurikuler: {prestasi or ekskul or 'Aktif mengikuti kegiatan sekolah'}
- Presensi: Sakit {sakit} hari, Izin {izin} hari, Alpa {alpa} hari

Contoh format narasi:
Alhamdulillaah, ananda {first_name} menunjukkan perkembangan belajar yang membanggakan dengan rata-rata {rata_rata:.1f}, khususnya unggul pada {unggul_ringkas}, serta istiqomah dalam pembiasaan sholat berjamaah. Sebagai saran tindak lanjut di rumah, ananda diharapkan terus mengulang latihan pada {perlu_ringkas} didampingi orang tua. Semoga Allah senantiasa memberkahi ikhtiar belajar ananda. Barakallahu fiik.

Tuliskan 1 paragraf narasi rapor untuk ananda {first_name}:"""

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
                    "top_p": 0.85,
                    "num_predict": 220,
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
    yang disempurnakan oleh Model Local AI Ollama (qwen2.5:1.5b) untuk mata pelajaran tertentu.
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
