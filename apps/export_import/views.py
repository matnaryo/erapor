from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib import messages
from apps.master_akademik.models import Kelas, Semester, TahunAjaran
from apps.kurikulum.models import PembelajaranKelas
from .excel_services import (
    create_styled_excel_template,
    process_import_nilai_excel,
    generate_leger_excel
)

@login_required(login_url='login')
def export_import_center_view(request):
    """
    Pusat Manajemen Ekspor dan Impor Data Akademik & Penilaian Excel.
    """
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    sem_aktif = Semester.objects.filter(is_active=True).first()
    
    kelas_id = request.GET.get('kelas')
    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif).order_by('tingkat', 'nama')
    selected_kelas = Kelas.objects.filter(id=kelas_id).first() if kelas_id else kelas_list.first()

    pembelajaran_list = []
    if selected_kelas and sem_aktif:
        pembelajaran_list = PembelajaranKelas.objects.filter(
            kelas=selected_kelas,
            semester=sem_aktif
        ).select_related('mata_pelajaran', 'guru_pengampu').order_by('mata_pelajaran__urutan')

    context = {
        'ta_aktif': ta_aktif,
        'sem_aktif': sem_aktif,
        'kelas_list': kelas_list,
        'selected_kelas': selected_kelas,
        'pembelajaran_list': pembelajaran_list,
    }
    return render(request, 'export_import/center.html', context)


@login_required(login_url='login')
def download_template_view(request, pembelajaran_id):
    """
    Mengunduh berkas template Excel (.xlsx) untuk mata pelajaran dan kelas tertentu.
    """
    pembelajaran = get_object_or_404(
        PembelajaranKelas.objects.select_related('kelas', 'mata_pelajaran', 'semester', 'kelas__tahun_ajaran'),
        id=pembelajaran_id
    )
    excel_buffer = create_styled_excel_template(pembelajaran)
    filename = f"Template_Nilai_{pembelajaran.kelas.nama}_{pembelajaran.mata_pelajaran.kode}.xlsx".replace(" ", "_")
    
    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url='login')
def import_nilai_view(request, pembelajaran_id):
    """
    Mengunggah dan mengimpor nilai dari berkas Excel (.xlsx).
    """
    pembelajaran = get_object_or_404(PembelajaranKelas, id=pembelajaran_id)

    if request.method == 'POST' and request.FILES.get('file_excel'):
        file_obj = request.FILES['file_excel']
        if not file_obj.name.endswith('.xlsx'):
            messages.error(request, "Format berkas harus berekstensi .xlsx (Excel)")
            return redirect('nilai_mupel_input', pembelajaran_id=pembelajaran.id)

        try:
            success_count, errors = process_import_nilai_excel(file_obj, pembelajaran)
            if success_count > 0:
                messages.success(request, f"Alhamdulillaah, berhasil mengimpor {success_count} nilai murid untuk mata pelajaran {pembelajaran.mata_pelajaran.nama}.")
            if errors:
                for err in errors[:5]:
                    messages.warning(request, err)
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat memproses berkas Excel: {str(e)}")

    return redirect('nilai_mupel_input', pembelajaran_id=pembelajaran.id)


@login_required(login_url='login')
def download_leger_view(request, kelas_id):
    """
    Mengunduh buku Leger Nilai lengkap 1 kelas dalam format Excel (.xlsx).
    """
    kelas = get_object_or_404(Kelas.objects.select_related('wali_kelas', 'tahun_ajaran'), id=kelas_id)
    sem_aktif = Semester.objects.filter(is_active=True).first()
    if not sem_aktif:
        raise Http404("Semester aktif belum ditentukan.")

    excel_buffer = generate_leger_excel(kelas, sem_aktif)
    filename = f"Leger_Nilai_Kelas_{kelas.nama}_Sem{sem_aktif.semester}.xlsx".replace(" ", "_")

    response = HttpResponse(
        excel_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
