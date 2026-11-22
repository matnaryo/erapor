from django.db import models
from apps.core.models import Pendidik
from apps.master_akademik.models import Fase, Kelas, Semester

class MataPelajaran(models.Model):
    """
    Master Mata Pelajaran:
    - Kategori: UMUM (1..8), PILIHAN (9..10), MULOK (11)
    - Urutan: Menentukan posisi baris baku pada dokumen rapor resmi.
    """
    KATEGORI_CHOICES = [
        ('UMUM', 'Mata Pelajaran Umum'),
        ('PILIHAN', 'Mata Pelajaran Pilihan'),
        ('MULOK', 'Muatan Lokal'),
    ]

    kode = models.CharField(max_length=20, unique=True, verbose_name="Kode Mupel (e.g. PAI, KKA)")
    nama = models.CharField(max_length=150, verbose_name="Nama Resmi Mata Pelajaran")
    kategori = models.CharField(max_length=15, choices=KATEGORI_CHOICES, default='UMUM')
    urutan = models.IntegerField(default=1, verbose_name="Urutan Tampil di Rapor")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Mata Pelajaran"
        verbose_name_plural = "Mata Pelajaran"
        ordering = ['urutan', 'nama']

    def __str__(self):
        return f"{self.urutan}. {self.nama} ({self.get_kategori_display()})"


class KKTPRentang(models.Model):
    """
    Kriteria Ketercapaian Tujuan Pembelajaran (KKTP) Dinamis.
    Rentang predikat dan label naratif per mupel dan fase.
    """
    PREDIKAT_CHOICES = [
        ('A', 'Sangat Baik (A)'),
        ('B', 'Baik (B)'),
        ('C', 'Cukup (C)'),
        ('D', 'Perlu Bimbingan (D)'),
    ]

    mata_pelajaran = models.ForeignKey(MataPelajaran, on_delete=models.CASCADE, related_name='kktp_rentang_list')
    fase = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='kktp_rentang_list')
    predikat = models.CharField(max_length=2, choices=PREDIKAT_CHOICES, verbose_name="Predikat")
    label = models.CharField(max_length=100, verbose_name="Label Deskripsi (e.g. Sangat Baik, Baik)")
    nilai_min = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Batas Bawah Nilai")
    nilai_max = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Batas Atas Nilai")
    keterangan_default = models.TextField(blank=True, verbose_name="Format Frasa Standar (e.g. Murid menunjukkan penguasaan...)")

    class Meta:
        verbose_name = "KKTP Rentang Nilai Dinamis"
        verbose_name_plural = "KKTP Rentang Nilai Dinamis"
        unique_together = ['mata_pelajaran', 'fase', 'predikat']
        ordering = ['mata_pelajaran', 'fase', '-nilai_min']

    def __str__(self):
        return f"{self.mata_pelajaran.kode} - Fase {self.fase.kode} [{self.predikat} : {self.nilai_min}-{self.nilai_max}]"


class TujuanPembelajaran(models.Model):
    """
    Tujuan Pembelajaran (TP) per Mata Pelajaran, Fase, dan Tingkat Kelas.
    Menjadi basis perumusan deskripsi capaian tertinggi dan perlu bimbingan.
    """
    mata_pelajaran = models.ForeignKey(MataPelajaran, on_delete=models.CASCADE, related_name='tp_list')
    fase = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='tp_list')
    tingkat = models.IntegerField(verbose_name="Tingkat Kelas (1-6)")
    semester = models.IntegerField(choices=[(1, '1 (satu)'), (2, '2 (dua)')], default=1)
    kode = models.CharField(max_length=20, verbose_name="Kode TP (e.g. TP 1.1)")
    deskripsi = models.TextField(verbose_name="Deskripsi Capaian TP")
    urutan = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Tujuan Pembelajaran (TP)"
        verbose_name_plural = "Tujuan Pembelajaran (TP)"
        ordering = ['mata_pelajaran', 'tingkat', 'semester', 'urutan']

    def __str__(self):
        return f"{self.mata_pelajaran.kode} Kls {self.tingkat} Sem {self.semester} - {self.kode}"


class PembelajaranKelas(models.Model):
    """
    Penugasan mengajar: Guru mengajar Mata Pelajaran tertentu di Kelas tertentu pada Semester aktif.
    """
    kelas = models.ForeignKey(Kelas, on_delete=models.CASCADE, related_name='pembelajaran_list')
    mata_pelajaran = models.ForeignKey(MataPelajaran, on_delete=models.CASCADE, related_name='pembelajaran_kelas')
    guru_pengampu = models.ForeignKey(Pendidik, on_delete=models.CASCADE, related_name='jadwal_mengajar')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='pembelajaran_list')
    tp_deskripsi_json = models.JSONField(
        default=dict,
        blank=True,
        editable=False,
        verbose_name="Keterangan Deskripsi TP 1-15 (JSON)",
        help_text="Menyimpan deskripsi materi TP 1 s/d TP 15 untuk pembelajaran ini."
    )

    class Meta:
        verbose_name = "Plotting Guru Pengampu"
        verbose_name_plural = "Plotting Guru Pengampu"
        unique_together = ['kelas', 'mata_pelajaran', 'semester']
        ordering = ['kelas', 'mata_pelajaran__urutan']

    def __str__(self):
        return f"{self.kelas.nama} - {self.mata_pelajaran.nama} ({self.guru_pengampu.nama_lengkap})"
