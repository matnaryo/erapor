from django.db import models
from django.contrib.auth.models import User

class Sekolah(models.Model):
    """
    Profil lembaga sekolah SDIT Luqman Al Hakim Sleman.
    Tunggal (Singleton) sebagai identitas resmi institusi.
    """
    nama = models.CharField(
        max_length=255, 
        default="SD Islam Terpadu Luqman Al Hakim Sleman",
        verbose_name="Nama Sekolah"
    )
    npsn = models.CharField(max_length=20, default="20401127", verbose_name="NPSN")
    nss = models.CharField(max_length=30, blank=True, verbose_name="NSS")
    alamat = models.TextField(
        default="Jl. Palagan Tentara Pelajar No. 52 Sedan, Sariharjo, Ngaglik, Sleman, D.I. Yogyakarta 55581",
        verbose_name="Alamat Lengkap"
    )
    desa_kelurahan = models.CharField(max_length=100, default="Sariharjo")
    kecamatan = models.CharField(max_length=100, default="Ngaglik")
    kabupaten_kota = models.CharField(max_length=100, default="Sleman")
    provinsi = models.CharField(max_length=100, default="D.I. Yogyakarta")
    kode_pos = models.CharField(max_length=10, default="55581")
    titimangsa_default = models.CharField(max_length=100, default="Sleman", verbose_name="Kota Titimangsa")
    
    kepala_sekolah_nama = models.CharField(max_length=200, blank=True, verbose_name="Nama Kepala Sekolah")
    kepala_sekolah_nip = models.CharField(max_length=50, blank=True, verbose_name="NIP/NIY Kepala Sekolah")
    
    kop_sekolah = models.ImageField(
        upload_to='kop_sekolah/', 
        blank=True, 
        null=True, 
        verbose_name="Gambar Kop Sekolah (Banner Resmi)"
    )
    logo_sekolah = models.ImageField(
        upload_to='logo/', 
        blank=True, 
        null=True, 
        verbose_name="Logo Sekolah"
    )

    class Meta:
        verbose_name = "Profil Sekolah"
        verbose_name_plural = "Profil Sekolah"

    def __str__(self):
        return self.nama


class Pendidik(models.Model):
    """
    Profil pendidik dan tenaga kependidikan (Data Pendidik).
    Mendukung penugasan peran RBAC.
    """
    ROLE_CHOICES = [
        ('SUPERADMIN', 'Superadmin / IT Admin'),
        ('KEPALA_SEKOLAH', 'Kepala Sekolah'),
        ('KURIKULUM', 'Tim Kurikulum'),
        ('WALI_KELAS', 'Wali Kelas'),
        ('GURU_MAPEL', 'Guru Mata Pelajaran'),
        ('PEMBINA_EKSKUL', 'Pembina Ekstrakurikuler'),
    ]

    GENDER_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil_pendidik')
    nama_lengkap = models.CharField(max_length=200, verbose_name="Nama Lengkap & Gelar")
    nip = models.CharField(max_length=50, blank=True, verbose_name="NIP")
    niy = models.CharField(max_length=50, blank=True, verbose_name="NIY (Nomor Induk Yayasan)")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='GURU_MAPEL', verbose_name="Peran RBAC")
    jenis_kelamin = models.CharField(max_length=1, choices=GENDER_CHOICES, default='L')
    no_hp = models.CharField(max_length=25, blank=True, verbose_name="No. WhatsApp / HP")
    tanda_tangan_digital = models.ImageField(upload_to='ttd_pendidik/', blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")

    class Meta:
        verbose_name = "Data Pendidik"
        verbose_name_plural = "Data Pendidik"
        ordering = ['nama_lengkap']

    def __str__(self):
        return f"{self.nama_lengkap} ({self.get_role_display()})"
