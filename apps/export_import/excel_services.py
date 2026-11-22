import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from decimal import Decimal
from apps.master_akademik.models import AnggotaKelas
from apps.penilaian.models import NilaiAkhir, Ketidakhadiran
from apps.penilaian.services import get_kktp_and_predikat, generate_capaian_kompetensi

def create_styled_excel_template(pembelajaran):
    """
    Membuat file template Excel (.xlsx) resmi untuk input nilai akhir per mata pelajaran.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Format Nilai"

    # Palet Warna & Font Resmi eLHaEs
    header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid") # Emerald Dark
    sub_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # Emerald Light
    font_title = Font(name="Calibri", size=14, bold=True, color="065F46")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='A0AEC0'),
        right=Side(style='thin', color='A0AEC0'),
        top=Side(style='thin', color='A0AEC0'),
        bottom=Side(style='thin', color='A0AEC0')
    )

    # Identitas Header Dokumen
    ws['A1'] = "FORMAT IMPOR NILAI AKHIR - e-RAPOR eLHaEs"
    ws['A1'].font = font_title
    
    ws['A3'] = "Sekolah"
    ws['B3'] = ": SDIT Luqman Al Hakim Sleman"
    ws['A4'] = "Kelas"
    ws['B4'] = f": {pembelajaran.kelas.nama}"
    ws['A5'] = "Mata Pelajaran"
    ws['B5'] = f": {pembelajaran.mata_pelajaran.nama} ({pembelajaran.mata_pelajaran.kategori})"
    ws['A6'] = "Semester / T.A."
    ws['B6'] = f": {pembelajaran.semester.semester} / {pembelajaran.kelas.tahun_ajaran.nama}"

    for r in range(3, 7):
        ws[f'A{r}'].font = font_bold

    # Kolom Tabel Input
    headers = [
        ("No", 6),
        ("NISN", 16),
        ("NIS", 14),
        ("Nama Lengkap Murid", 36),
        ("Nilai Akhir (0-100)", 20),
        ("Capaian Tertinggi (Opsional)", 45),
        ("Capaian Perlu Bimbingan (Opsional)", 45),
    ]

    header_row = 8
    for col_num, (h_title, width) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num, value=h_title)
        cell.font = font_header
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        col_letter = openpyxl.utils.get_column_letter(col_num)
        ws.column_dimensions[col_letter].width = width

    ws.row_dimensions[header_row].height = 28

    # Isi Data Murid
    anggota_list = AnggotaKelas.objects.filter(kelas=pembelajaran.kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')
    nilai_dict = {
        n.anggota_kelas_id: n for n in NilaiAkhir.objects.filter(
            pembelajaran_kelas=pembelajaran,
            anggota_kelas__in=anggota_list
        )
    }

    start_row = 9
    for idx, anggota in enumerate(anggota_list, 1):
        current_row = start_row + idx - 1
        n_obj = nilai_dict.get(anggota.id)

        ws.cell(row=current_row, column=1, value=anggota.nomor_absen or idx).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=2, value=anggota.murid.nisn).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=3, value=anggota.murid.nis).alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=4, value=anggota.murid.nama_lengkap)
        
        c_nilai = ws.cell(row=current_row, column=5, value=float(n_obj.nilai_angka) if n_obj else "")
        c_nilai.alignment = Alignment(horizontal="center")
        c_nilai.font = font_bold
        
        ws.cell(row=current_row, column=6, value=n_obj.capaian_tertinggi if n_obj else "")
        ws.cell(row=current_row, column=7, value=n_obj.capaian_perlu_bimbingan if n_obj else "")

        for col_idx in range(1, 8):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.border = thin_border
            if not cell.font or cell.font == font_bold:
                pass
            else:
                cell.font = font_regular

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def process_import_nilai_excel(file_obj, pembelajaran):
    """
    Membaca dan memvalidasi file Excel yang diunggah, lalu menyimpan nilai ke database.
    """
    wb = openpyxl.load_workbook(file_obj, data_only=True)
    ws = wb.active

    kelas = pembelajaran.kelas
    fase = kelas.fase
    sem = pembelajaran.semester
    mupel = pembelajaran.mata_pelajaran

    anggota_map = {
        str(a.murid.nisn).strip(): a for a in AnggotaKelas.objects.filter(kelas=kelas).select_related('murid')
    }

    success_count = 0
    errors = []

    for row_idx in range(9, ws.max_row + 1):
        nisn_val = str(ws.cell(row=row_idx, column=2).value or '').strip()
        nilai_val = ws.cell(row=row_idx, column=5).value
        tertinggi_val = str(ws.cell(row=row_idx, column=6).value or '').strip()
        perlu_val = str(ws.cell(row=row_idx, column=7).value or '').strip()

        if not nisn_val:
            continue

        anggota = anggota_map.get(nisn_val)
        if not anggota:
            errors.append(f"Baris {row_idx}: NISN {nisn_val} tidak terdaftar di kelas {kelas.nama}.")
            continue

        if nilai_val is not None and str(nilai_val).strip() != '':
            try:
                nilai_angka = float(nilai_val)
                predikat, _ = get_kktp_and_predikat(nilai_angka, mupel, fase)

                # Jika narasi kosong, generate otomatis dari KKTP & TP
                if not tertinggi_val:
                    predikat, tertinggi_val, perlu_val = generate_capaian_kompetensi(
                        nilai_angka, mupel, fase, semester=sem.semester, tingkat=kelas.tingkat
                    )

                NilaiAkhir.objects.update_or_create(
                    anggota_kelas=anggota,
                    pembelajaran_kelas=pembelajaran,
                    defaults={
                        'nilai_angka': nilai_angka,
                        'predikat': predikat,
                        'capaian_tertinggi': tertinggi_val,
                        'capaian_perlu_bimbingan': perlu_val
                    }
                )
                success_count += 1
            except ValueError:
                errors.append(f"Baris {row_idx}: Nilai '{nilai_val}' bukan angka yang valid.")

    return success_count, errors


def generate_leger_excel(kelas, semester):
    """
    Membuat buku Leger Nilai Rapor lengkap 1 kelas dalam format Excel (.xlsx).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Leger Kelas {kelas.nama}"

    font_title = Font(name="Calibri", size=14, bold=True, color="065F46")
    header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color='A0AEC0'), right=Side(style='thin', color='A0AEC0'),
        top=Side(style='thin', color='A0AEC0'), bottom=Side(style='thin', color='A0AEC0')
    )

    ws['A1'] = f"LEGER NILAI HASIL BELAJAR - SDIT LUQMAN AL HAKIM SLEMAN"
    ws['A1'].font = font_title
    ws['A2'] = f"Kelas: {kelas.nama} | Semester: {semester.semester} | T.A.: {kelas.tahun_ajaran.nama} | Wali Kelas: {kelas.wali_kelas.nama_lengkap}"
    ws['A2'].font = font_bold

    headers = ["No", "NISN", "NIS", "Nama Murid"]
    from apps.kurikulum.models import MataPelajaran
    mupel_list = list(MataPelajaran.objects.filter(is_active=True).order_by('urutan'))
    for m in mupel_list:
        headers.append(m.kode)
    headers.extend(["Rata-rata", "Sakit", "Izin", "Alpa"])

    header_row = 4
    for col_idx, h_name in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h_name)
        cell.font = font_header
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = 18 if col_idx == 4 else (10 if col_idx > 4 else 8)

    ws.column_dimensions['D'].width = 32

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen', 'murid__nama_lengkap')
    absen_dict = {a.anggota_kelas_id: a for a in Ketidakhadiran.objects.filter(semester=semester, anggota_kelas__in=anggota_list)}
    
    from apps.kurikulum.models import PembelajaranKelas
    pembelajaran_map = {
        p.mata_pelajaran_id: p for p in PembelajaranKelas.objects.filter(kelas=kelas, semester=semester)
    }

    start_row = 5
    for idx, anggota in enumerate(anggota_list, 1):
        cur_row = start_row + idx - 1
        ws.cell(row=cur_row, column=1, value=anggota.nomor_absen or idx).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=2, value=anggota.murid.nisn).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=3, value=anggota.murid.nis).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=4, value=anggota.murid.nama_lengkap)

        nilai_totals = []
        col_cursor = 5
        for m in mupel_list:
            pemb = pembelajaran_map.get(m.id)
            n_obj = NilaiAkhir.objects.filter(anggota_kelas=anggota, pembelajaran_kelas=pemb).first() if pemb else None
            if n_obj and n_obj.nilai_angka is not None:
                val = float(n_obj.nilai_angka)
                nilai_totals.append(val)
                ws.cell(row=cur_row, column=col_cursor, value=round(val, 1)).alignment = Alignment(horizontal="center")
            else:
                ws.cell(row=cur_row, column=col_cursor, value="-").alignment = Alignment(horizontal="center")
            col_cursor += 1

        avg_val = round(sum(nilai_totals) / len(nilai_totals), 1) if nilai_totals else 0
        c_avg = ws.cell(row=cur_row, column=col_cursor, value=avg_val)
        c_avg.alignment = Alignment(horizontal="center")
        c_avg.font = font_bold
        col_cursor += 1

        ab = absen_dict.get(anggota.id)
        ws.cell(row=cur_row, column=col_cursor, value=ab.sakit if ab else 0).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=col_cursor+1, value=ab.izin if ab else 0).alignment = Alignment(horizontal="center")
        ws.cell(row=cur_row, column=col_cursor+2, value=ab.tanpa_keterangan if ab else 0).alignment = Alignment(horizontal="center")

        for c in range(1, len(headers) + 1):
            ws.cell(row=cur_row, column=c).border = thin_border

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
