from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.core.decorators import role_required
from apps.master_akademik.models import Fase, Semester, TahunAjaran
from .models import MataPelajaran, KKTPRentang, TujuanPembelajaran, PembelajaranKelas, TPKokurikuler

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


@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def kokurikuler_tp_view(request):
    """
    Submenu Input TP Kokurikuler (Maksimal 7 TP):
    Menentukan deskripsi rumusan TP Kokurikuler 1 s/d 7 per Tingkat Kelas & Semester.
    """
    sem_aktif = Semester.objects.filter(is_active=True).first()
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    pendidik = getattr(request.user, 'profil_pendidik', None)

    if getattr(request.user, 'role', '') == 'WALI_KELAS' and pendidik:
        kelas_asuhan = pendidik.kelas_asuhan.filter(tahun_ajaran=ta_aktif).first() or pendidik.kelas_asuhan.first()
        selected_tingkat = kelas_asuhan.tingkat if kelas_asuhan else 1
    else:
        selected_tingkat = int(request.GET.get('tingkat', 1))

    selected_sem = int(request.GET.get('sem', sem_aktif.semester if sem_aktif else 1))

    fase_kode = 'A' if selected_tingkat in [1, 2] else ('B' if selected_tingkat in [3, 4] else 'C')
    fase = Fase.objects.filter(kode=fase_kode).first()

    if request.method == 'POST':
        for i in range(1, 8):
            kode = request.POST.get(f"tp_{i}_kode", f"TP {i}").strip()
            desk = request.POST.get(f"tp_{i}_deskripsi", "").strip()
            if desk:
                TPKokurikuler.objects.update_or_create(
                    tingkat=selected_tingkat,
                    semester=selected_sem,
                    nomor=i,
                    defaults={
                        'fase': fase,
                        'kode': kode or f"TP {i}",
                        'deskripsi': desk,
                        'urutan': i
                    }
                )
        messages.success(request, f"Alhamdulillaah, Tujuan Pembelajaran Kokurikuler Kelas {selected_tingkat} Semester {selected_sem} berhasil disimpan.")
        return redirect(f"{request.path}?tingkat={selected_tingkat}&sem={selected_sem}")

    tp_items = []
    tp_qs = {t.nomor: t for t in TPKokurikuler.objects.filter(tingkat=selected_tingkat, semester=selected_sem)}
    for i in range(1, 8):
        existing = tp_qs.get(i)
        tp_items.append({
            'nomor': i,
            'kode': existing.kode if existing else f"TP {i}",
            'deskripsi': existing.deskripsi if existing else "",
        })

    context = {
        'selected_tingkat': selected_tingkat,
        'selected_sem': selected_sem,
        'fase': fase,
        'tp_items': tp_items,
        'tingkat_list': list(range(1, 7)),
    }
    return render(request, 'kurikulum/kokurikuler_tp_list.html', context)

