from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Max
from apps.core.decorators import role_required
from .models import Murid, Kelas, AnggotaKelas, TahunAjaran
from .forms import MuridForm

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS', 'KEPALA_SEKOLAH'])
def murid_list_view(request):
    """Menampilkan daftar seluruh murid dengan fitur pencarian dan filter."""
    query = request.GET.get('q', '').strip()
    kelas_id = request.GET.get('kelas', '')
    gender = request.GET.get('gender', '')

    murid_qs = Murid.objects.filter(is_active=True).order_by('nama_lengkap')

    if query:
        murid_qs = murid_qs.filter(
            Q(nama_lengkap__icontains=query) |
            Q(nisn__icontains=query) |
            Q(nis__icontains=query)
        )

    if gender in ['L', 'P']:
        murid_qs = murid_qs.filter(jenis_kelamin=gender)

    if kelas_id:
        murid_qs = murid_qs.filter(riwayat_kelas__kelas_id=kelas_id)

    paginator = Paginator(murid_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    kelas_list = Kelas.objects.filter(tahun_ajaran=ta_aktif) if ta_aktif else Kelas.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'kelas_id': kelas_id,
        'gender': gender,
        'kelas_list': kelas_list,
        'total_hasil': murid_qs.count(),
    }
    return render(request, 'master_akademik/murid_list.html', context)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS', 'KEPALA_SEKOLAH'])
def murid_detail_view(request, pk):
    """Menampilkan detail buku induk identitas murid."""
    murid = get_object_or_404(Murid, pk=pk)
    riwayat_kelas = AnggotaKelas.objects.filter(murid=murid).select_related('kelas', 'kelas__tahun_ajaran', 'kelas__wali_kelas')
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    kelas_list_aktif = Kelas.objects.filter(tahun_ajaran=ta_aktif).select_related('wali_kelas') if ta_aktif else Kelas.objects.all()
    context = {
        'murid': murid,
        'riwayat_kelas': riwayat_kelas,
        'ta_aktif': ta_aktif,
        'kelas_list_aktif': kelas_list_aktif,
    }
    return render(request, 'master_akademik/murid_detail.html', context)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def murid_create_view(request):
    """Formulir pendaftaran / input murid baru."""
    target_kelas_id = request.GET.get('kelas')
    target_kelas = Kelas.objects.filter(id=target_kelas_id).first() if target_kelas_id else None

    if request.method == 'POST':
        form = MuridForm(request.POST, request.FILES, user=request.user, target_kelas=target_kelas)
        if form.is_valid():
            murid = form.save()
            kelas_tujuan = form.cleaned_data.get('kelas_tujuan')
            nomor_absen = form.cleaned_data.get('nomor_absen')
            
            if kelas_tujuan:
                if not nomor_absen:
                    last_absen = AnggotaKelas.objects.filter(kelas=kelas_tujuan).aggregate(Max('nomor_absen'))['nomor_absen__max']
                    nomor_absen = (last_absen or 0) + 1
                elif AnggotaKelas.objects.filter(kelas=kelas_tujuan, nomor_absen=nomor_absen).exists():
                    last_absen = AnggotaKelas.objects.filter(kelas=kelas_tujuan).aggregate(Max('nomor_absen'))['nomor_absen__max']
                    nomor_absen = (last_absen or 0) + 1
                
                AnggotaKelas.objects.get_or_create(
                    kelas=kelas_tujuan,
                    murid=murid,
                    defaults={'nomor_absen': nomor_absen}
                )
                messages.success(request, f"Data murid '{murid.nama_lengkap}' berhasil ditambahkan dan ditempatkan di Kelas {kelas_tujuan.nama} (Presensi #{nomor_absen}).")
            else:
                messages.success(request, f"Data murid '{murid.nama_lengkap}' berhasil ditambahkan ke Buku Induk.")
            
            return redirect('murid_detail', pk=murid.pk)
    else:
        form = MuridForm(user=request.user, target_kelas=target_kelas)

    return render(request, 'master_akademik/murid_form.html', {'form': form, 'title': 'Tambah Data Murid Baru', 'target_kelas': target_kelas})

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def murid_update_view(request, pk):
    """Formulir penyuntingan data murid."""
    murid = get_object_or_404(Murid, pk=pk)
    if request.method == 'POST':
        form = MuridForm(request.POST, request.FILES, instance=murid, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Perubahan data murid '{murid.nama_lengkap}' berhasil disimpan.")
            return redirect('murid_detail', pk=murid.pk)
    else:
        form = MuridForm(instance=murid, user=request.user)

    return render(request, 'master_akademik/murid_form.html', {'form': form, 'title': f'Sunting Data Murid: {murid.nama_lengkap}', 'murid': murid})

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def murid_tempatkan_kelas_view(request, pk):
    """Menempatkan murid ke kelas tertentu langsung dari halaman detail murid."""
    if request.method != 'POST':
        return redirect('murid_detail', pk=pk)
    
    murid = get_object_or_404(Murid, pk=pk)
    kelas_id = request.POST.get('kelas_id')
    kelas = get_object_or_404(Kelas, pk=kelas_id)
    
    # Validasi wewenang jika Wali Kelas
    profil = getattr(request.user, 'profil_pendidik', None)
    if not request.user.is_superuser and profil and profil.role == 'WALI_KELAS':
        if kelas.wali_kelas != profil:
            messages.error(request, "Anda hanya dapat menempatkan murid ke kelas binaan Anda.")
            return redirect('murid_detail', pk=pk)

    # Cek apakah sudah terdaftar di kelas tahun ajaran ini
    existing = AnggotaKelas.objects.filter(kelas__tahun_ajaran=kelas.tahun_ajaran, murid=murid).first()
    if existing:
        messages.warning(request, f"Murid '{murid.nama_lengkap}' sudah terdaftar di Kelas {existing.kelas.nama} untuk Tahun Ajaran {kelas.tahun_ajaran.nama}.")
        return redirect('murid_detail', pk=pk)

    nomor_absen = request.POST.get('nomor_absen')
    try:
        nomor_absen = int(nomor_absen)
    except (TypeError, ValueError):
        nomor_absen = None

    if not nomor_absen or AnggotaKelas.objects.filter(kelas=kelas, nomor_absen=nomor_absen).exists():
        max_absen = AnggotaKelas.objects.filter(kelas=kelas).aggregate(Max('nomor_absen'))['nomor_absen__max']
        nomor_absen = (max_absen or 0) + 1

    AnggotaKelas.objects.create(
        kelas=kelas,
        murid=murid,
        nomor_absen=nomor_absen
    )
    messages.success(request, f"Alhamdulillah! Murid '{murid.nama_lengkap}' berhasil ditempatkan di Kelas {kelas.nama} (Nomor Presensi #{nomor_absen}).")
    return redirect('murid_detail', pk=pk)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS', 'KEPALA_SEKOLAH'])
def kelas_list_view(request):
    """Daftar rombongan belajar / kelas dan wali kelas."""
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    kelas_qs = Kelas.objects.filter(tahun_ajaran=ta_aktif).select_related('wali_kelas', 'fase').order_by('tingkat', 'nama')
    return render(request, 'master_akademik/kelas_list.html', {'kelas_list': kelas_qs, 'ta_aktif': ta_aktif})

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def kelas_anggota_view(request, pk):
    """Mengelola keanggotaan / plotting murid dalam satu rombel kelas."""
    kelas = get_object_or_404(Kelas.objects.select_related('tahun_ajaran', 'fase', 'wali_kelas'), pk=pk)
    
    # Validasi hak akses: Wali kelas hanya boleh kelola kelasnya sendiri
    profil = getattr(request.user, 'profil_pendidik', None)
    if not request.user.is_superuser and profil and profil.role == 'WALI_KELAS':
        if kelas.wali_kelas != profil:
            messages.error(request, "Anda tidak memiliki wewenang untuk mengelola rombel selain kelas asuhan Anda.")
            return redirect('kelas_list')

    if request.method == 'POST':
        action = request.POST.get('action', 'tambah')
        
        if action == 'tambah':
            murid_id = request.POST.get('murid_id')
            murid = get_object_or_404(Murid, pk=murid_id, is_active=True)
            
            # Cek apakah murid sudah punya kelas di tahun ajaran ini
            existing = AnggotaKelas.objects.filter(kelas__tahun_ajaran=kelas.tahun_ajaran, murid=murid).first()
            if existing:
                messages.warning(request, f"Murid '{murid.nama_lengkap}' sudah terdaftar di Kelas {existing.kelas.nama} (T.A. {kelas.tahun_ajaran.nama}).")
            else:
                nomor_absen = request.POST.get('nomor_absen')
                try:
                    nomor_absen = int(nomor_absen)
                except (TypeError, ValueError):
                    nomor_absen = None
                
                if not nomor_absen or AnggotaKelas.objects.filter(kelas=kelas, nomor_absen=nomor_absen).exists():
                    max_absen = AnggotaKelas.objects.filter(kelas=kelas).aggregate(Max('nomor_absen'))['nomor_absen__max']
                    nomor_absen = (max_absen or 0) + 1
                
                AnggotaKelas.objects.create(
                    kelas=kelas,
                    murid=murid,
                    nomor_absen=nomor_absen
                )
                messages.success(request, f"Murid '{murid.nama_lengkap}' berhasil dimasukkan ke Kelas {kelas.nama} dengan nomor presensi {nomor_absen}.")
        
        elif action == 'update_absen':
            # Update nomor presensi
            for key, val in request.POST.items():
                if key.startswith('absen_'):
                    try:
                        anggota_id = int(key.replace('absen_', ''))
                        no_baru = int(val)
                        AnggotaKelas.objects.filter(id=anggota_id, kelas=kelas).update(nomor_absen=no_baru)
                    except ValueError:
                        pass
            messages.success(request, "Perubahan nomor presensi berhasil disimpan.")
            
        return redirect('kelas_anggota', pk=kelas.pk)

    anggota_list = AnggotaKelas.objects.filter(kelas=kelas).select_related('murid').order_by('nomor_absen')
    
    # Murid aktif yang belum memiliki kelas di tahun ajaran ini
    murid_tersedia = Murid.objects.filter(
        is_active=True
    ).exclude(
        riwayat_kelas__kelas__tahun_ajaran=kelas.tahun_ajaran
    ).order_by('nama_lengkap')
    
    last_absen = anggota_list.aggregate(Max('nomor_absen'))['nomor_absen__max']
    next_absen = (last_absen or 0) + 1

    context = {
        'kelas': kelas,
        'anggota_list': anggota_list,
        'murid_tersedia': murid_tersedia,
        'next_absen': next_absen,
        'total_anggota': anggota_list.count(),
    }
    return render(request, 'master_akademik/kelas_anggota.html', context)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def kelas_hapus_anggota_view(request, kelas_id, anggota_id):
    """Mengeluarkan murid dari rombel kelas."""
    kelas = get_object_or_404(Kelas, pk=kelas_id)
    
    profil = getattr(request.user, 'profil_pendidik', None)
    if not request.user.is_superuser and profil and profil.role == 'WALI_KELAS':
        if kelas.wali_kelas != profil:
            messages.error(request, "Anda tidak memiliki wewenang untuk mengubah data rombel ini.")
            return redirect('kelas_list')

    anggota = get_object_or_404(AnggotaKelas, pk=anggota_id, kelas=kelas)
    nama_murid = anggota.murid.nama_lengkap
    
    if request.method == 'POST':
        anggota.delete()
        messages.info(request, f"Murid '{nama_murid}' telah dikeluarkan dari Kelas {kelas.nama}.")
    
    return redirect('kelas_anggota', pk=kelas.pk)
