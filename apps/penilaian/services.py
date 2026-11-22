from decimal import Decimal
from apps.kurikulum.models import KKTPRentang, TujuanPembelajaran, PembelajaranKelas, MataPelajaran

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
    Menghasilkan rumusan deskripsi capaian kompetensi otomatis:
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
