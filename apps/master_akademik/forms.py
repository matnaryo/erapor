from django import forms
from django.db.models import Max
from .models import Murid, Kelas, AnggotaKelas, TahunAjaran

class MuridForm(forms.ModelForm):
    kelas_tujuan = forms.ModelChoiceField(
        queryset=Kelas.objects.none(),
        required=False,
        label="Tempatkan ke Rombel / Kelas (T.A. Aktif)",
        empty_label="-- Pilih Kelas (Opsional) --"
    )
    nomor_absen = forms.IntegerField(
        required=False,
        min_value=1,
        label="Nomor Presensi / Urut"
    )

    class Meta:
        model = Murid
        fields = [
            'nama_lengkap', 'nis', 'nisn', 'jenis_kelamin', 
            'tempat_lahir', 'tanggal_lahir', 'agama', 'pendidikan_sebelumnya',
            'alamat_lengkap', 'desa_kelurahan', 'kecamatan', 'kabupaten_kota', 'provinsi', 'kode_pos',
            'nama_ayah', 'pekerjaan_ayah', 'nama_ibu', 'pekerjaan_ibu',
            'nama_wali', 'pekerjaan_wali', 'alamat_wali', 'foto', 'is_active'
        ]
        widgets = {
            'tanggal_lahir': forms.DateInput(attrs={'type': 'date'}),
            'alamat_lengkap': forms.Textarea(attrs={'rows': 2}),
            'alamat_wali': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, user=None, target_kelas=None, **kwargs):
        super().__init__(*args, **kwargs)
        base_classes = "w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 focus:bg-white transition outline-none"
        for field_name, field in self.fields.items():
            if field_name not in ['is_active']:
                field.widget.attrs['class'] = base_classes
            if field_name == 'is_active':
                field.widget.attrs['class'] = 'rounded text-emerald-600 focus:ring-emerald-500 h-4 w-4'

        ta_aktif = TahunAjaran.objects.filter(is_active=True).first()
        if ta_aktif:
            self.fields['kelas_tujuan'].queryset = Kelas.objects.filter(tahun_ajaran=ta_aktif).order_by('tingkat', 'nama')
        else:
            self.fields['kelas_tujuan'].queryset = Kelas.objects.all().order_by('tingkat', 'nama')

        if target_kelas:
            self.fields['kelas_tujuan'].initial = target_kelas
            max_absen = AnggotaKelas.objects.filter(kelas=target_kelas).aggregate(Max('nomor_absen'))['nomor_absen__max']
            self.fields['nomor_absen'].initial = (max_absen or 0) + 1
        elif user and hasattr(user, 'profil_pendidik') and user.profil_pendidik.role == 'WALI_KELAS':
            kelas_wali = Kelas.objects.filter(wali_kelas=user.profil_pendidik, tahun_ajaran=ta_aktif).first()
            if kelas_wali:
                self.fields['kelas_tujuan'].initial = kelas_wali
                max_absen = AnggotaKelas.objects.filter(kelas=kelas_wali).aggregate(Max('nomor_absen'))['nomor_absen__max']
                self.fields['nomor_absen'].initial = (max_absen or 0) + 1
