from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from apps.core.decorators import role_required
from .models import Murid, Kelas, AnggotaKelas, TahunAjaran
from .forms import MuridForm

@login_required(login_url='login')
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
def murid_detail_view(request, pk):
    """Menampilkan detail buku induk identitas murid."""
    murid = get_object_or_404(Murid, pk=pk)
    riwayat_kelas = AnggotaKelas.objects.filter(murid=murid).select_related('kelas', 'kelas__tahun_ajaran')
    context = {
        'murid': murid,
        'riwayat_kelas': riwayat_kelas,
    }
    return render(request, 'master_akademik/murid_detail.html', context)

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def murid_create_view(request):
    """Formulir pendaftaran / input murid baru."""
    if request.method == 'POST':
        form = MuridForm(request.POST, request.FILES)
        if form.is_valid():
            murid = form.save()
            messages.success(request, f"Data murid '{murid.nama_lengkap}' berhasil ditambahkan.")
            return redirect('murid_detail', pk=murid.pk)
    else:
        form = MuridForm()

    return render(request, 'master_akademik/murid_form.html', {'form': form, 'title': 'Tambah Data Murid Baru'})

@login_required(login_url='login')
@role_required(['SUPERADMIN', 'KURIKULUM', 'WALI_KELAS'])
def murid_update_view(request, pk):
    """Formulir penyuntingan data murid."""
    murid = get_object_or_404(Murid, pk=pk)
    if request.method == 'POST':
        form = MuridForm(request.POST, request.FILES, instance=murid)
        if form.is_valid():
            form.save()
            messages.success(request, f"Perubahan data murid '{murid.nama_lengkap}' berhasil disimpan.")
            return redirect('murid_detail', pk=murid.pk)
    else:
        form = MuridForm(instance=murid)

    return render(request, 'master_akademik/murid_form.html', {'form': form, 'title': f'Sunting Data Murid: {murid.nama_lengkap}', 'murid': murid})

@login_required(login_url='login')
def kelas_list_view(request):
    """Daftar rombongan belajar / kelas dan wali kelas."""
    ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
    kelas_qs = Kelas.objects.filter(tahun_ajaran=ta_aktif).select_related('wali_kelas', 'fase').order_by('tingkat', 'nama')
    return render(request, 'master_akademik/kelas_list.html', {'kelas_list': kelas_qs, 'ta_aktif': ta_aktif})
