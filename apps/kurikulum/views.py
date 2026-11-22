from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.core.decorators import role_required
from apps.master_akademik.models import Fase
from .models import MataPelajaran, KKTPRentang, TujuanPembelajaran, PembelajaranKelas

@login_required(login_url='login')
def mupel_list_view(request):
    """Menampilkan Mata Pelajaran Resmi SDIT Luqman Al Hakim Sleman."""
    pendidik = getattr(request.user, 'profil_pendidik', None)

    mupel_umum = MataPelajaran.objects.filter(kategori='UMUM', is_active=True).order_by('urutan')
    mupel_pilihan = MataPelajaran.objects.filter(kategori='PILIHAN', is_active=True).order_by('urutan')
    mupel_mulok = MataPelajaran.objects.filter(kategori='MULOK', is_active=True).order_by('urutan')

    if pendidik and pendidik.role == 'GURU_MAPEL':
        ampu_mupel_ids = PembelajaranKelas.objects.filter(
            guru_pengampu=pendidik
        ).values_list('mata_pelajaran_id', flat=True).distinct()
        mupel_umum = mupel_umum.filter(id__in=ampu_mupel_ids)
        mupel_pilihan = mupel_pilihan.filter(id__in=ampu_mupel_ids)
        mupel_mulok = mupel_mulok.filter(id__in=ampu_mupel_ids)

    context = {
        'mupel_umum': mupel_umum,
        'mupel_pilihan': mupel_pilihan,
        'mupel_mulok': mupel_mulok,
    }
    return render(request, 'kurikulum/mupel_list.html', context)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM'])
def kktp_manage_view(request):
    """
    Manajemen Kriteria Ketercapaian Tujuan Pembelajaran (KKTP) Dinamis.
    Rentang predikat (A, B, C, D) dan interval nilai dapat disesuaikan per Mupel dan Fase.
    """
    mupel_id = request.GET.get('mupel')
    fase_kode = request.GET.get('fase', 'A')

    fase_list = Fase.objects.all().order_by('kode')
    mupel_list = MataPelajaran.objects.filter(is_active=True).order_by('urutan')

    selected_fase = Fase.objects.filter(kode=fase_kode).first() or fase_list.first()
    selected_mupel = MataPelajaran.objects.filter(id=mupel_id).first() if mupel_id else mupel_list.first()

    kktp_items = []
    if selected_mupel and selected_fase:
        kktp_items = KKTPRentang.objects.filter(
            mata_pelajaran=selected_mupel,
            fase=selected_fase
        ).order_by('-nilai_min')

    if request.method == 'POST':
        # Simpan pembaruan rentang KKTP
        for item in kktp_items:
            prefix = f"kktp_{item.id}_"
            n_min = request.POST.get(f"{prefix}min")
            n_max = request.POST.get(f"{prefix}max")
            label = request.POST.get(f"{prefix}label")
            ket = request.POST.get(f"{prefix}ket")

            if n_min and n_max:
                item.nilai_min = float(n_min)
                item.nilai_max = float(n_max)
                if label: item.label = label
                if ket is not None: item.keterangan_default = ket
                item.save()

        messages.success(request, f"Rentang KKTP untuk {selected_mupel.nama} (Fase {selected_fase.kode}) berhasil disimpan.")
        return redirect(f"{request.path}?mupel={selected_mupel.id}&fase={selected_fase.kode}")

    context = {
        'fase_list': fase_list,
        'mupel_list': mupel_list,
        'selected_fase': selected_fase,
        'selected_mupel': selected_mupel,
        'kktp_items': kktp_items,
    }
    return render(request, 'kurikulum/kktp_list.html', context)

@login_required(login_url='login')
def tp_list_view(request):
    """Daftar Tujuan Pembelajaran (TP) per Mata Pelajaran dan Fase."""
    mupel_id = request.GET.get('mupel')
    fase_kode = request.GET.get('fase', 'A')
    semester = request.GET.get('sem', '1')

    pendidik = getattr(request.user, 'profil_pendidik', None)

    fase_list = Fase.objects.all().order_by('kode')
    mupel_list = MataPelajaran.objects.filter(is_active=True).order_by('urutan')

    if pendidik and pendidik.role == 'GURU_MAPEL':
        ampu_mupel_ids = PembelajaranKelas.objects.filter(
            guru_pengampu=pendidik
        ).values_list('mata_pelajaran_id', flat=True).distinct()
        mupel_list = mupel_list.filter(id__in=ampu_mupel_ids)

    selected_fase = Fase.objects.filter(kode=fase_kode).first() or fase_list.first()
    selected_mupel = mupel_list.filter(id=mupel_id).first() if mupel_id else mupel_list.first()

    tp_items = []
    if selected_mupel and selected_fase:
        tp_items = TujuanPembelajaran.objects.filter(
            mata_pelajaran=selected_mupel,
            fase=selected_fase,
            semester=int(semester)
        ).order_by('tingkat', 'urutan')

    if request.method == 'POST' and request.user.is_staff:
        # Tambah TP baru
        kode = request.POST.get('kode', '').strip()
        deskripsi = request.POST.get('deskripsi', '').strip()
        tingkat = request.POST.get('tingkat', '1')
        urutan = request.POST.get('urutan', '1')

        if kode and deskripsi and selected_mupel and selected_fase:
            TujuanPembelajaran.objects.create(
                mata_pelajaran=selected_mupel,
                fase=selected_fase,
                tingkat=int(tingkat),
                semester=int(semester),
                kode=kode,
                deskripsi=deskripsi,
                urutan=int(urutan)
            )
            messages.success(request, f"Tujuan Pembelajaran {kode} berhasil ditambahkan.")
            return redirect(f"{request.path}?mupel={selected_mupel.id}&fase={selected_fase.kode}&sem={semester}")

    context = {
        'fase_list': fase_list,
        'mupel_list': mupel_list,
        'selected_fase': selected_fase,
        'selected_mupel': selected_mupel,
        'selected_sem': int(semester),
        'tp_items': tp_items,
    }
    return render(request, 'kurikulum/tp_list.html', context)
