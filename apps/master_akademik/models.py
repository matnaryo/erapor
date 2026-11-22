from django.db import models
from apps.core.models import Pendidik

class TahunAjaran(models.Model):
    """
    Tahun Ajaran Akademik (e.g. 2026/2027)
    """
    nama = models.CharField(max_length=20, unique=True, verbose_name="Tahun Ajaran (e.g. 2026/2027)")
    tanggal_mulai = models.DateField(verbose_name="Tanggal Mulai")
    tanggal_selesai = models.DateField(verbose_name="Tanggal Selesai")
    is_active = models.BooleanField(default=False, verbose_name="Tahun Ajaran Aktif")

    class Meta:
        verbose_name = "Tahun Ajaran"
        verbose_name_plural = "Tahun Ajaran"
        ordering = ['-nama']

    def __str__(self):
        return f"{self.nama}{' (Aktif)' if self.is_active else ''}"


class Semester(models.Model):
    """
    Semester Ganjil (1) atau Genap (2)
    """
    SEMESTER_CHOICES = [
        (1, '1 (satu) / Ganjil'),
        (2, '2 (dua) / Genap'),
    ]

    tahun_ajaran = models.ForeignKey(TahunAjaran, on_delete=models.CASCADE, related_name='semester_list')
    semester = models.IntegerField(choices=SEMESTER_CHOICES, default=1, verbose_name="Semester")
    titimangsa_tanggal = models.DateField(verbose_name="Tanggal Pembagian Rapor")
    titimangsa_tempat = models.CharField(max_length=100, default="Sleman", verbose_name="Tempat Titimangsa")
    is_active = models.BooleanField(default=False, verbose_name="Semester Aktif")

    class Meta:
        verbose_name = "Semester"
        verbose_name_plural = "Semester"
        unique_together = ['tahun_ajaran', 'semester']
        ordering = ['tahun_ajaran', 'semester']

    def __str__(self):
        return f"{self.tahun_ajaran.nama} - Semester {self.semester}{' (Aktif)' if self.is_active else ''}"


class Fase(models.Model):
    """
    Fase Kurikulum Merdeka:
    Fase A (Kelas 1-2), Fase B (Kelas 3-4), Fase C (Kelas 5-6)
    """
    kode = models.CharField(max_length=5, unique=True, verbose_name="Kode Fase (A/B/C)")
    nama = models.CharField(max_length=100, verbose_name="Nama Fase")
    deskripsi = models.TextField(blank=True, verbose_name="Keterangan")

    class Meta:
        verbose_name = "Fase Kurikulum Merdeka"
        verbose_name_plural = "Fase Kurikulum Merdeka"
        ordering = ['kode']

    def __str__(self):
        return f"Fase {self.kode} ({self.nama})"


class Kelas(models.Model):
    """
    Rombongan Belajar / Kelas Murid
    """
    tahun_ajaran = models.ForeignKey(TahunAjaran, on_delete=models.CASCADE, related_name='kelas_list')
    fase = models.ForeignKey(Fase, on_delete=models.PROTECT, related_name='kelas_list')
    tingkat = models.IntegerField(verbose_name="Tingkat Kelas (1-6)")
    nama = models.CharField(max_length=50, verbose_name="Nama Kelas (e.g. I, II, I A)")
    wali_kelas = models.ForeignKey(
        Pendidik, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='kelas_asuhan',
        verbose_name="Wali Kelas"
    )

    class Meta:
        verbose_name = "Kelas / Rombel"
        verbose_name_plural = "Kelas / Rombel"
        unique_together = ['tahun_ajaran', 'nama']
        ordering = ['tingkat', 'nama']

    def __str__(self):
        return f"Kelas {self.nama} ({self.tahun_ajaran.nama})"


class Murid(models.Model):
    """
    Data Induk Murid (Buku Induk & Identitas Resmi).
    Terminologi baku: "Murid" (bukan siswa / peserta didik).
    """
    GENDER_CHOICES = [
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ]

    nama_lengkap = models.CharField(max_length=200, verbose_name="Nama Lengkap Murid")
    nis = models.CharField(max_length=20, verbose_name="Nomor Induk Sekolah (NIS)")
    nisn = models.CharField(max_length=20, unique=True, verbose_name="NISN")
    jenis_kelamin = models.CharField(max_length=1, choices=GENDER_CHOICES, default='L')
    tempat_lahir = models.CharField(max_length=100, verbose_name="Tempat Lahir")
    tanggal_lahir = models.DateField(verbose_name="Tanggal Lahir")
    agama = models.CharField(max_length=50, default="Islam", verbose_name="Agama")
    pendidikan_sebelumnya = models.CharField(max_length=100, blank=True, verbose_name="Pendidikan Sebelumnya (TK/RA)")
    
    # Data Alamat
    alamat_lengkap = models.TextField(verbose_name="Alamat Lengkap")
    desa_kelurahan = models.CharField(max_length=100, blank=True, verbose_name="Desa / Kelurahan")
    kecamatan = models.CharField(max_length=100, blank=True, verbose_name="Kecamatan")
    kabupaten_kota = models.CharField(max_length=100, blank=True, verbose_name="Kabupaten / Kota")
    provinsi = models.CharField(max_length=100, blank=True, verbose_name="Provinsi")
    kode_pos = models.CharField(max_length=10, blank=True, verbose_name="Kode Pos")

    # Data Orang Tua / Wali
    nama_ayah = models.CharField(max_length=200, blank=True, verbose_name="Nama Ayah")
    pekerjaan_ayah = models.CharField(max_length=100, blank=True, verbose_name="Pekerjaan Ayah")
    nama_ibu = models.CharField(max_length=200, blank=True, verbose_name="Nama Ibu")
    pekerjaan_ibu = models.CharField(max_length=100, blank=True, verbose_name="Pekerjaan Ibu")
    nama_wali = models.CharField(max_length=200, blank=True, verbose_name="Nama Wali (Jika Ada)")
    pekerjaan_wali = models.CharField(max_length=100, blank=True, verbose_name="Pekerjaan Wali")
    alamat_wali = models.TextField(blank=True, verbose_name="Alamat Wali")

    foto = models.ImageField(upload_to='foto_murid/', blank=True, null=True, verbose_name="Pas Foto")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")

    class Meta:
        verbose_name = "Data Murid"
        verbose_name_plural = "Data Murid"
        ordering = ['nama_lengkap']

    def __str__(self):
        return f"{self.nama_lengkap} (NISN: {self.nisn})"


class AnggotaKelas(models.Model):
    """
    Relasi penempatan murid di kelas pada tahun ajaran tertentu.
    """
    kelas = models.ForeignKey(Kelas, on_delete=models.CASCADE, related_name='anggota_list')
    murid = models.ForeignKey(Murid, on_delete=models.CASCADE, related_name='riwayat_kelas')
    nomor_absen = models.IntegerField(verbose_name="Nomor Presensi / Urut")

    class Meta:
        verbose_name = "Anggota Kelas"
        verbose_name_plural = "Anggota Kelas"
        unique_together = [['kelas', 'murid'], ['kelas', 'nomor_absen']]
        ordering = ['kelas', 'nomor_absen']

    def __str__(self):
        return f"{self.nomor_absen}. {self.murid.nama_lengkap} - {self.kelas.nama}"
