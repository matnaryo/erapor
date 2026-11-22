import requests
import json
import logging

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:3b"

def generate_wali_kelas_note(nama_murid, panggilan="ananda", nilai_summary="", kokurikuler="", prestasi="", sakit=0, izin=0, alpa=0):
    """
    Menghasilkan draft narasi Catatan Wali Kelas bernuansa Islami khas SDIT Luqman Al Hakim Sleman
    menggunakan model Local AI Ollama qwen2.5-coder:3b.
    Menyediakan graceful fallback otomatis jika layanan offline/timeout.
    """
    system_prompt = (
        "Anda adalah asisten AI resmi SDIT Luqman Al Hakim Sleman (SDIT eLHaEs). "
        "Tugas Anda adalah menulis narasi Catatan Wali Kelas untuk buku rapor semester sekolah dasar. "
        "Gunakan bahasa Indonesia yang santun, hangat, apresiatif, mendidik, dan bernuansa islami. "
        "Catatan HARUS berupa 1 paragraf utuh (3-5 kalimat), tanpa poin-poin/bullet, diawali rasa syukur/apresiasi "
        "(seperti 'Alhamdulillaah...'), dan diakhiri doa/harapan berkah ('Barakallahu fiik'). "
        "Fokus pada pembiasaan adab, ibadah (sholat/tahfidz), dan semangat belajar."
    )

    user_prompt = f"""Nama Murid: {nama_murid}
Catatan capaian akademik: {nilai_summary or 'Menunjukkan ketuntasan belajar yang baik di seluruh mata pelajaran'}
Kokurikuler & adab: {kokurikuler or 'Tertib dalam sholat dhuha berjamaah dan hafalan tahfidz'}
Prestasi & ekskul: {prestasi or 'Aktif mengikuti kegiatan ekstrakurikuler kepanduan siaga'}
Presensi: Sakit {sakit} hari, Izin {izin} hari, Alpa {alpa} hari.

Tolong buatkan teks narasi Catatan Wali Kelas (hanya 1 paragraf langsung teks catatan tanpa kata pengantar tambahan):"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 200,
                }
            },
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            output_text = result.get("response", "").strip()
            # Bersihkan jika ada tanda petik ganda pembungkus
            if output_text.startswith('"') and output_text.endswith('"'):
                output_text = output_text[1:-1].strip()
            if output_text:
                return output_text, True, user_prompt

    except Exception as e:
        logger.warning(f"Ollama local AI request failed: {e}. Menggunakan fallback template berbasis aturan.")

    # Rule-based dynamic fallback jika Ollama offline
    first_name = nama_murid.split()[0]
    fallback_text = (
        f"Alhamdulillaah, ananda {first_name} menunjukkan semangat belajar yang sangat menggembirakan "
        f"serta peningkatan pembiasaan adab dan ketertiban sholat berjamaah di semester ini. "
        f"Pertahankan ketekunan dalam muraja'ah hafalan Al-Qur'an dan tingkatkan ketelitian dalam latihan berhitung mandiri. "
        f"Semoga Allah Subhanahu wa Ta'ala senantiasa menganugerahkan ilmu yang bermanfaat, menjaga ananda menjadi generasi sholih yang cerdas dan berakhlak mulia. "
        f"Barakallahu fiik."
    )
    return fallback_text, False, "Fallback Rule-Based Engine"
