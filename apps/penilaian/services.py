from decimal import Decimal
from apps.kurikulum.models import KKTPRentang, TujuanPembelajaran, PembelajaranKelas, MataPelajaran

DEFAULT_TP_TEMPLATES = {
    'PAI': {
        1: "memahami huruf hijaiyah berharakat dan surat-surat pendek Juz 30",
        2: "mengenal rukun Islam, rukun iman, dan kalimah thayyibah",
        3: "mempraktikkan tata cara bersuci (wudhu) dan sholat fardhu secara tertib",
        4: "meneladani kisah keteladanan Nabi Muhammad SAW dan para sahabat",
        5: "menerapkan adab makan, minum, dan adab islami harian",
    },
    'PP': {
        1: "mengenal simbol dan sila-sila Pancasila dalam lambang negara",
        2: "mengidentifikasi aturan dan kesepakatan bersama di rumah dan kelas",
        3: "menunjukkan sikap menghargai keberagaman identitas dan budaya teman",
        4: "mempraktikkan musyawarah sederhana dan gotong royong di lingkungan sekolah",
    },
    'BIN': {
        1: "menyimak dan menceritakan kembali isi teks narasi sederhana dengan santun",
        2: "mengeja suku kata dan memperkaya kosa kata baru melalui gambar",
        3: "menulis kalimat sederhana menggunakan huruf kapital dan tanda titik secara tepat",
        4: "membaca lancar kata-kata sederhana dengan lafal dan intonasi yang jelas",
    },
    'MTK': {
        1: "membilang cacah lambang bilangan hingga 20 secara terurut",
        2: "menyelesaikan operasi hitung penjumlahan dan pengurangan konkrit",
        3: "mengidentifikasi dan mengelompokkan bentuk bangun datar bersudut sederhana",
        4: "mengukur dan membandingkan panjang dan berat benda menggunakan satuan konkrit",
    },
    'IPAS': {
        1: "mengenali bagian-bagian tubuh dan cara merawat kebersihan diri",
        2: "menceritakan silsilah keluarga inti dan denah lingkungan sekitar rumah",
        3: "mengidentifikasi benda dan wujud materi di lingkungan sekitar",
        4: "menjelaskan peran lingkungan alam dan lingkungan buatan serta pelestariannya",
    },
    'PJOK': {
        1: "mempraktikkan keterampilan pola gerak dasar lokomotor jalan, lari, dan lompat",
        2: "mempraktikkan pola gerak non-lokomotor memutar, menekuk, dan mengayun",
        3: "menjaga kebersihan diri dan kebugaran jasmani setelah berolahraga",
    },
    'SR': {
        1: "mengeksplorasi garis, bentuk geometris dasar, dan paduan warna cerah",
        2: "membuat karya kolase dan mozaik menggunakan bahan alami di lingkungan",
    },
    'SM': {
        1: "mengenal pola irama dan birama lagu anak-anak bertema islami",
        2: "menyanyikan lagu nasional dan lagu anak dengan ketukan yang tepat",
    },
    'BIG': {
        1: "mengenal salam sapaan (greetings) dan ungkapan perkenalan diri sederhana",
        2: "menyebutkan kosa kata anggota keluarga, warna, dan angka 1 sampai 20",
    },
    'BJAW': {
        1: "mengenal tembang dolanan anak dan kosa kata unggah-ungguh basa Jawa",
        2: "nyritakake pengalamane kanthi basa Jawa prasaja kang becik",
    },
    'KKA': {
        1: "mengenal pola logika berpikir komputasional dan algoritma sederhana",
        2: "mengidentifikasi instruksi berurutan melalui permainan edukasi konkrit",
    },
}

def get_tp_descriptions(pembelajaran):
    """
    Mengambil deskripsi Tujuan Pembelajaran (TP 1 s/d TP 15) untuk satu pembelajaran.
    Prioritas:
    1. tp_deskripsi_json yang disunting guru pada PembelajaranKelas.
    2. Master data TujuanPembelajaran di database (berdasarkan tingkat kelas spesifik).
    3. Template bawaan kurikulum standar per mata pelajaran (jika belum ada master TP).
    Hanya mengembalikan TP yang benar-benar telah dirumuskan / aktif.
    """
    mupel = pembelajaran.mata_pelajaran
    custom_json = pembelajaran.tp_deskripsi_json or {}
    
    # Ambil dari master TujuanPembelajaran jika ada (utamakan berdasarkan tingkat kelas)
    master_tp = {}
    master_qs = TujuanPembelajaran.objects.filter(
        mata_pelajaran=mupel,
        tingkat=pembelajaran.kelas.tingkat,
        semester=pembelajaran.semester.semester
    ).order_by('urutan')

    # Fallback ke fase jika belum ada filter tingkat spesifik (misal data legacy)
    if not master_qs.exists() and pembelajaran.kelas.fase:
        master_qs = TujuanPembelajaran.objects.filter(
            mata_pelajaran=mupel,
            fase=pembelajaran.kelas.fase,
            semester=pembelajaran.semester.semester
        ).order_by('urutan')

    for tp in master_qs:
        if tp.deskripsi and tp.deskripsi.strip():
            master_tp[tp.urutan] = tp.deskripsi.strip()

    template_mupel = DEFAULT_TP_TEMPLATES.get(mupel.kode, {})

    tp_dict = {}
    for i in range(1, 16):
        str_key = str(i)
        if str_key in custom_json and isinstance(custom_json[str_key], str) and custom_json[str_key].strip():
            tp_dict[i] = custom_json[str_key].strip()
        elif i in master_tp and master_tp[i].strip():
            tp_dict[i] = master_tp[i].strip()
        elif i in template_mupel and template_mupel[i].strip():
            tp_dict[i] = template_mupel[i].strip()
        # Catatan: Kolom yang belum memiliki rumusan TP dibiarkan kosong (tidak ada key i)
        # agar pada matriks penilaian otomatis terkunci (disabled) dan tidak bisa diedit.

    return tp_dict


def calculate_from_tp_scores(nilai_tp_dict, tp_descriptions, mata_pelajaran, fase):
    """
    Menghitung Nilai Akhir (rata-rata TP terisi), Predikat, serta merumuskan
    Capaian Tertinggi dan Capaian Terendah / Perlu Bimbingan berdasarkan nilai TP yang ada.
    """
    filled_tps = {}
    for k, v in nilai_tp_dict.items():
        try:
            num_k = int(k)
            if v is not None and str(v).strip() != "":
                val_float = float(str(v).replace(',', '.'))
                if 0 <= val_float <= 100:
                    filled_tps[num_k] = val_float
        except (ValueError, TypeError):
            continue

    if not filled_tps:
        return None, "", "", "", None, None

    nilai_angka = round(sum(filled_tps.values()) / len(filled_tps), 2)
    predikat, kktp = get_kktp_and_predikat(nilai_angka, mata_pelajaran, fase)

    # TP tertinggi dan terendah
    max_tp = max(filled_tps, key=lambda k: (filled_tps[k], -k))
    min_tp = min(filled_tps, key=lambda k: (filled_tps[k], k))
    max_val = filled_tps[max_tp]
    min_val = filled_tps[min_tp]

    max_desc = tp_descriptions.get(max_tp, f"materi TP {max_tp}").strip()
    min_desc = tp_descriptions.get(min_tp, f"materi TP {min_tp}").strip()

    # Rumusan Capaian Tertinggi
    if max_val >= 88:
        prefix_max = "Murid menunjukkan penguasaan yang sangat baik dalam"
    elif max_val >= 76:
        prefix_max = "Murid menunjukkan penguasaan yang baik dalam"
    elif max_val >= 65:
        prefix_max = "Murid cukup mampu dalam"
    else:
        prefix_max = "Murid mulai berkembang dalam"

    clean_max_desc = max_desc[0].lower() + max_desc[1:] if len(max_desc) > 1 else max_desc.lower()
    if clean_max_desc.startswith("murid "):
        capaian_tertinggi = max_desc
    else:
        capaian_tertinggi = f"{prefix_max} {clean_max_desc}."

    # Rumusan Capaian Terendah / Perlu Bimbingan
    if len(filled_tps) > 1:
        if min_val < 76:
            prefix_min = "Murid perlu bimbingan dalam"
        elif min_val < 85:
            prefix_min = "Murid perlu peningkatan dan penguatan dalam"
        else:
            prefix_min = "Murid menunjukkan penguasaan yang cukup baik dalam"
        
        clean_min_desc = min_desc[0].lower() + min_desc[1:] if len(min_desc) > 1 else min_desc.lower()
        if clean_min_desc.startswith("murid "):
            capaian_perlu = min_desc
        else:
            capaian_perlu = f"{prefix_min} {clean_min_desc}."
    else:
        capaian_perlu = ""

    return nilai_angka, predikat, capaian_tertinggi, capaian_perlu, max_tp, min_tp


def get_kktp_and_predikat(nilai_angka, mata_pelajaran, fase):
    """
    Menentukan predikat (A, B, C, D) dan KKTP rentang berdasarkan nilai angka (0-100),
    mata pelajaran, dan fase murid.
    """
    nilai = Decimal(str(nilai_angka))
    rentang_list = KKTPRentang.objects.filter(
        mata_pelajaran=mata_pelajaran,
        fase=fase
    ).order_by('-nilai_min')

    for r in rentang_list:
        if r.nilai_min <= nilai <= r.nilai_max:
            return r.predikat, r

    # Fallback jika di luar rentang
    if nilai >= 88:
        return 'A', None
    elif nilai >= 76:
        return 'B', None
    elif nilai >= 65:
        return 'C', None
    else:
        return 'D', None


def generate_capaian_kompetensi(nilai_angka, mata_pelajaran, fase, semester=1, tingkat=1):
    """
    Menghasilkan rumusan deskripsi capaian kompetensi otomatis (fungsi kompatibilitas):
    - capaian_tertinggi: narasi penguasaan materi terbaik.
    - capaian_perlu_bimbingan: narasi aspek materi yang perlu bimbingan/peningkatan.
    """
    predikat, kktp = get_kktp_and_predikat(nilai_angka, mata_pelajaran, fase)
    
    tp_qs = TujuanPembelajaran.objects.filter(
        mata_pelajaran=mata_pelajaran,
        fase=fase,
        semester=semester
    ).order_by('urutan')

    tp_list = list(tp_qs)

    prefix_a = "Murid menunjukkan penguasaan yang sangat baik dalam"
    prefix_b = "Murid menunjukkan penguasaan yang baik dalam"
    prefix_c = "Murid cukup mampu dalam"
    prefix_d = "Murid perlu bimbingan dalam"

    if kktp and kktp.keterangan_default:
        prefix_tertinggi = kktp.keterangan_default
    elif predikat == 'A':
        prefix_tertinggi = prefix_a
    elif predikat == 'B':
        prefix_tertinggi = prefix_b
    elif predikat == 'C':
        prefix_tertinggi = prefix_c
    else:
        prefix_tertinggi = prefix_d

    tp_tertinggi_desc = tp_list[0].deskripsi if tp_list else "materi dan tujuan pembelajaran semester ini."
    
    # Capaian Perlu Bimbingan (jika ada lebih dari 1 TP atau predikat < A)
    if len(tp_list) > 1 and predikat in ['A', 'B']:
        tp_lanjutan_desc = tp_list[1].deskripsi
        if predikat == 'A':
            capaian_perlu = f"Murid menunjukkan penguasaan yang baik dalam {tp_lanjutan_desc.lower()}"
        else:
            capaian_perlu = f"Murid perlu bimbingan dalam {tp_lanjutan_desc.lower()}"
    elif len(tp_list) > 1 and predikat in ['C', 'D']:
        tp_lanjutan_desc = tp_list[1].deskripsi
        capaian_perlu = f"Murid perlu bimbingan intensif dalam {tp_lanjutan_desc.lower()}"
    else:
        capaian_perlu = ""

    capaian_tertinggi = f"{prefix_tertinggi} {tp_tertinggi_desc.lower() if not tp_tertinggi_desc.startswith('Murid') else tp_tertinggi_desc}"

    return predikat, capaian_tertinggi, capaian_perlu

    tp_tertinggi_desc = tp_list[0].deskripsi if tp_list else "materi dan tujuan pembelajaran semester ini."
    
    # Capaian Perlu Bimbingan (jika ada lebih dari 1 TP atau predikat < A)
    if len(tp_list) > 1 and predikat in ['A', 'B']:
        # Jika nilai sangat baik, TP kedua tetap baik atau penguatan lanjutan
        tp_lanjutan_desc = tp_list[1].deskripsi
        if predikat == 'A':
            capaian_perlu = f"Murid menunjukkan penguasaan yang baik dalam {tp_lanjutan_desc.lower()}"
        else:
            capaian_perlu = f"Murid perlu bimbingan dalam {tp_lanjutan_desc.lower()}"
    elif len(tp_list) > 1 and predikat in ['C', 'D']:
        tp_lanjutan_desc = tp_list[1].deskripsi
        capaian_perlu = f"Murid perlu bimbingan intensif dalam {tp_lanjutan_desc.lower()}"
    else:
        capaian_perlu = ""

    capaian_tertinggi = f"{prefix_tertinggi} {tp_tertinggi_desc.lower() if not tp_tertinggi_desc.startswith('Murid') else tp_tertinggi_desc}"

    return predikat, capaian_tertinggi, capaian_perlu

def ensure_pembelajaran_kelas(kelas, semester, guru_pengampu):
    """
    Memastikan 11 mata pelajaran resmi terdaftar sebagai PembelajaranKelas untuk kelas dan semester terkait.
    """
    mupel_all = MataPelajaran.objects.filter(is_active=True).order_by('urutan')
    created_count = 0
    for mupel in mupel_all:
        obj, created = PembelajaranKelas.objects.get_or_create(
            kelas=kelas,
            mata_pelajaran=mupel,
            semester=semester,
            defaults={'guru_pengampu': guru_pengampu}
        )
        if created:
            created_count += 1
    return created_count


def get_koku_predikat_and_ket(score):
    """
    Konversi Nilai Skala 4 Kokurikuler ke Predikat dan Keterangan:
    3.20 - 4.00  : A (sangat baik)
    2.80 - 3.19  : B (baik)
    2.40 - 2.79  : C (cukup baik)
    0.00 - 2.39  : D (perlu bimbingan)
    """
    if score is None:
        return 'A', 'sangat baik'
    try:
        val = float(score)
    except (ValueError, TypeError):
        return 'A', 'sangat baik'
    
    # Jika input dalam skala 100 (> 4.0), konversikan otomatis ke skala 4
    if val > 4.0:
        val = min(4.0, round(val / 25.0, 2))
    else:
        val = round(val, 2)
        
    if val >= 3.20:
        return 'A', 'sangat baik'
    elif val >= 2.80:
        return 'B', 'baik'
    elif val >= 2.40:
        return 'C', 'cukup baik'
    else:
        return 'D', 'perlu bimbingan'


def generate_kokurikuler_combined_deskripsi(tp_data_list):
    """
    Menghasilkan gabungan deskripsi dari ke-7 TP kokurikuler:
    tp_data_list: list of dict {'nomor': i, 'avg': float, 'predikat': 'A', 'ket': 'sangat baik', 'deskripsi': '...'}
    Sesuai format narasi capaian Kokurikuler di view rapor Halaman 3 e-Rapor eLHaEs.
    """
    phrases = []
    for item in tp_data_list:
        ket = item.get('ket', 'sangat baik')
        raw_desk = (item.get('deskripsi') or '').strip()
        if not raw_desk:
            continue
        # Rapikan deskripsi: jika diawali 'Murid ...', bersihkan
        if raw_desk.lower().startswith('murid '):
            raw_desk = raw_desk[6:].strip()
        # Huruf pertama lowercase dan hapus tanda titik di akhir
        clean_desk = raw_desk[0].lower() + raw_desk[1:] if len(raw_desk) > 1 else raw_desk.lower()
        clean_desk = clean_desk.rstrip('.')
        
        phrases.append(f"{ket} dalam {clean_desk}")
        
    if not phrases:
        return "Murid sangat baik dalam membiasakan ibadah dan adab islami di sekolah."
        
    if len(phrases) == 1:
        return f"Murid {phrases[0]}."
    
    # Gabungkan dengan koma, dan frasa terakhir diawali 'serta'
    gabungan = ", ".join(phrases[:-1]) + ", serta " + phrases[-1] + "."
    return f"Murid {gabungan}"
