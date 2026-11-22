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
    """
    Daftar, Filter, Tambah, Edit, dan Hapus Tujuan Pembelajaran (TP).
    Dikelompokkan berdasarkan Tingkat Kelas (1 s/d 6) bukan sekadar Fase.
    Guru Mapel dapat memilih tingkat kelas dan mupel yang diampu secara fleksibel.
    """
    mupel_id = request.GET.get('mupel')
    tingkat_param = request.GET.get('tingkat', '')
    fase_param = request.GET.get('fase', '')
    semester = request.GET.get('sem', '1')

    pendidik = getattr(request.user, 'profil_pendidik', None)

    fase_list = Fase.objects.all().order_by('kode')
    mupel_list = MataPelajaran.objects.filter(is_active=True).order_by('urutan')

    guru_tingkat_list = []
    if pendidik and pendidik.role == 'GURU_MAPEL':
        ampu_mupel_ids = PembelajaranKelas.objects.filter(
            guru_pengampu=pendidik
        ).values_list('mata_pelajaran_id', flat=True).distinct()
        mupel_list = mupel_list.filter(id__in=ampu_mupel_ids)
        guru_tingkat_list = list(PembelajaranKelas.objects.filter(
            guru_pengampu=pendidik
        ).values_list('kelas__tingkat', flat=True).distinct().order_by('kelas__tingkat'))

    selected_mupel = mupel_list.filter(id=mupel_id).first() if mupel_id else mupel_list.first()

    # Opsi pilihan Tingkat Kelas (1 s/d 6)
    tingkat_options = []
    for t in range(1, 7):
        f_k = 'A' if t in [1, 2] else ('B' if t in [3, 4] else 'C')
        is_ampu = (t in guru_tingkat_list) if (pendidik and pendidik.role == 'GURU_MAPEL') else True
        tingkat_options.append({
            'tingkat': t,
            'fase_kode': f_k,
            'is_ampu': is_ampu,
            'label': f"Kelas {t} (Fase {f_k})"
        })

    # Tentukan selected_tingkat
    if tingkat_param in ['1', '2', '3', '4', '5', '6']:
        selected_tingkat = int(tingkat_param)
    elif tingkat_param == 'all':
        selected_tingkat = 'all'
    else:
        # Default: tampilkan semua tingkat agar tidak ada TP yang tersembunyi
        selected_tingkat = 'all'

    # Tentukan selected_fase
    if selected_tingkat != 'all':
        fase_kode = 'A' if selected_tingkat in [1, 2] else ('B' if selected_tingkat in [3, 4] else 'C')
        selected_fase = Fase.objects.filter(kode=fase_kode).first()
    elif fase_param in ['A', 'B', 'C']:
        selected_fase = Fase.objects.filter(kode=fase_param).first()
    else:
        selected_fase = None

    # Handle POST Actions: Add, Edit, Delete
    if request.method == 'POST':
        action = request.POST.get('action', 'add')

        # Cek izin akses: Superuser, Staff, atau Pendidik yang berwenang
        is_authorized = (
            request.user.is_superuser or 
            request.user.is_staff or 
            (pendidik and pendidik.role in ['SUPERADMIN', 'KEPALA_SEKOLAH', 'KURIKULUM', 'WALI_KELAS', 'GURU_MAPEL'])
        )

        if not is_authorized:
            messages.error(request, "Akses ditolak: Anda tidak memiliki wewenang untuk mengelola Tujuan Pembelajaran.")
            return redirect(f"{request.path}?mupel={selected_mupel.id if selected_mupel else ''}&tingkat={selected_tingkat}&sem={semester}")

        if action == 'add':
            kode = request.POST.get('kode', '').strip()
            deskripsi = request.POST.get('deskripsi', '').strip()
            t_input = int(request.POST.get('tingkat', 1 if selected_tingkat == 'all' else selected_tingkat))
            u_input = int(request.POST.get('urutan', 1))
            f_kode = 'A' if t_input in [1, 2] else ('B' if t_input in [3, 4] else 'C')
            f_obj = Fase.objects.filter(kode=f_kode).first()

            if kode and deskripsi and selected_mupel:
                TujuanPembelajaran.objects.create(
                    mata_pelajaran=selected_mupel,
                    fase=f_obj,
                    tingkat=t_input,
                    semester=int(semester),
                    kode=kode,
                    deskripsi=deskripsi,
                    urutan=u_input
                )
                messages.success(request, f"Tujuan Pembelajaran {kode} (Kelas {t_input}) berhasil ditambahkan.")
            return redirect(f"{request.path}?mupel={selected_mupel.id}&tingkat={t_input}&sem={semester}")

        elif action == 'edit':
            tp_id = request.POST.get('tp_id')
            tp = get_object_or_404(TujuanPembelajaran, id=tp_id)
            kode = request.POST.get('kode', '').strip()
            deskripsi = request.POST.get('deskripsi', '').strip()
            t_input = int(request.POST.get('tingkat', tp.tingkat))
            u_input = int(request.POST.get('urutan', tp.urutan))
            f_kode = 'A' if t_input in [1, 2] else ('B' if t_input in [3, 4] else 'C')
            f_obj = Fase.objects.filter(kode=f_kode).first()

            if kode and deskripsi:
                tp.kode = kode
                tp.deskripsi = deskripsi
                tp.tingkat = t_input
                tp.urutan = u_input
                if f_obj:
                    tp.fase = f_obj
                tp.save()
                messages.success(request, f"Tujuan Pembelajaran {tp.kode} berhasil diperbarui.")
            return redirect(f"{request.path}?mupel={tp.mata_pelajaran_id}&tingkat={t_input}&sem={tp.semester}")

        elif action == 'delete':
            tp_id = request.POST.get('tp_id')
            tp = get_object_or_404(TujuanPembelajaran, id=tp_id)
            m_id = tp.mata_pelajaran_id
            t_del = tp.tingkat
            sem_del = tp.semester
            kode_del = tp.kode
            tp.delete()
            messages.success(request, f"Tujuan Pembelajaran {kode_del} berhasil dihapus.")
            return redirect(f"{request.path}?mupel={m_id}&tingkat={t_del}&sem={sem_del}")

    # Query TP items
    tp_items = []
    if selected_mupel:
        tp_qs = TujuanPembelajaran.objects.filter(
            mata_pelajaran=selected_mupel,
            semester=int(semester)
        )
        if selected_tingkat != 'all':
            tp_qs = tp_qs.filter(tingkat=selected_tingkat)
        elif selected_fase:
            tp_qs = tp_qs.filter(fase=selected_fase)

        tp_items = list(tp_qs.order_by('tingkat', 'urutan'))

    # Kelompokkan TP berdasarkan Tingkat Kelas (1 s/d 6)
    if selected_tingkat != 'all':
        tingkat_display_list = [selected_tingkat]
    elif selected_fase:
        tingkat_display_list = [1, 2] if selected_fase.kode == 'A' else ([3, 4] if selected_fase.kode == 'B' else [5, 6])
    else:
        tingkat_display_list = list(range(1, 7))

    grouped_tp = []
    for t in tingkat_display_list:
        f_k = 'A' if t in [1, 2] else ('B' if t in [3, 4] else 'C')
        items = [tp for tp in tp_items if tp.tingkat == t]
        is_ampu = (t in guru_tingkat_list) if (pendidik and pendidik.role == 'GURU_MAPEL') else True
        next_urutan = (max([tp.urutan for tp in items], default=0) + 1) if items else 1
        grouped_tp.append({
            'tingkat': t,
            'fase_kode': f_k,
            'items': items,
            'count': len(items),
            'is_ampu': is_ampu,
            'next_urutan': next_urutan
        })

    context = {
        'fase_list': fase_list,
        'mupel_list': mupel_list,
        'tingkat_options': tingkat_options,
        'selected_fase': selected_fase,
        'selected_tingkat': selected_tingkat,
        'selected_mupel': selected_mupel,
        'selected_sem': int(semester),
        'tp_items': tp_items,
        'grouped_tp': grouped_tp,
        'guru_tingkat_list': guru_tingkat_list,
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

