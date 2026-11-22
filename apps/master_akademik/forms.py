from django import forms
from .models import Murid, Kelas, AnggotaKelas

class MuridForm(forms.ModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_classes = "w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 focus:bg-white transition outline-none"
        for field_name, field in self.fields.items():
            if field_name not in ['is_active']:
                field.widget.attrs['class'] = base_classes
            if field_name == 'is_active':
                field.widget.attrs['class'] = 'rounded text-emerald-600 focus:ring-emerald-500 h-4 w-4'
