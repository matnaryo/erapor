from django.db import models
from apps.master_akademik.models import AnggotaKelas, Semester
from apps.kurikulum.models import PembelajaranKelas

class NilaiAkhir(models.Model):
    """
    Nilai Akhir Rapor per Murid per Mata Pelajaran.
    Memuat nilai angka (skala 0-100), capaian kompetensi tertinggi, dan yang perlu bimbingan.
    """
    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='nilai_mupel_list')
    pembelajaran_kelas = models.ForeignKey(PembelajaranKelas, on_delete=models.CASCADE, related_name='nilai_list')
    nilai_angka = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Nilai Akhir (0-100)")
    predikat = models.CharField(max_length=5, blank=True, verbose_name="Predikat Terhitung (A/B/C/D)")
    
    capaian_tertinggi = models.TextField(
        verbose_name="Deskripsi Capaian Kompetensi Sangat Baik / Tertinggi",
        help_text="Frasa naratif capaian kompetensi tertinggi yang dikuasai murid."
    )
    capaian_perlu_bimbingan = models.TextField(
        blank=True,
        verbose_name="Deskripsi Capaian Kompetensi yang Perlu Bimbingan",
        help_text="Frasa naratif materi atau kompetensi yang perlu ditingkatkan/dibimbing."
    )
    nilai_tp = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Nilai Rincian TP 1-15 (JSON)",
        help_text="Menyimpan nilai TP 1 s/d TP 15, contoh: {'1': 85, '2': 90, ...}"
    )

    class Meta:
        verbose_name = "Nilai Akhir Mata Pelajaran"
        verbose_name_plural = "Nilai Akhir Mata Pelajaran"
        unique_together = ['anggota_kelas', 'pembelajaran_kelas']
        ordering = ['pembelajaran_kelas__mata_pelajaran__urutan']

    def __str__(self):
        return f"{self.anggota_kelas.murid.nama_lengkap} - {self.pembelajaran_kelas.mata_pelajaran.nama}: {self.nilai_angka}"


class NilaiTP(models.Model):
    """
    Rincian Nilai per Tujuan Pembelajaran (TP 1 s/d TP 15) per Murid per Mata Pelajaran.
    """
    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='nilai_tp_detail')
    pembelajaran_kelas = models.ForeignKey(PembelajaranKelas, on_delete=models.CASCADE, related_name='nilai_tp_detail')
    tp_nomor = models.IntegerField(verbose_name="Nomor TP (1-15)")
    nilai = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Nilai TP (0-100)")

    class Meta:
        verbose_name = "Nilai Tujuan Pembelajaran"
        verbose_name_plural = "Nilai Tujuan Pembelajaran"
        unique_together = ['anggota_kelas', 'pembelajaran_kelas', 'tp_nomor']
        ordering = ['anggota_kelas', 'tp_nomor']

    def __str__(self):
        return f"TP{self.tp_nomor}: {self.nilai} ({self.anggota_kelas.murid.nama_lengkap})"


class KokurikulerNilai(models.Model):
    """
    Nilai Kokurikuler (P5 / Karakter & Pembiasaan Islami SDIT Luqman Al Hakim Sleman).
    Contoh: Pembiasaan sholat dhuha, sholat berjamaah, hafalan tahfidz, adab makan islami, olahraga sportivitas.
    """
    PREDIKAT_CHOICES = [
        ('A', 'Sangat Baik (A)'),
        ('B', 'Baik (B)'),
        ('C', 'Cukup (C)'),
        ('D', 'Perlu Bimbingan (D)'),
    ]

    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='nilai_kokurikuler')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='kokurikuler_list')
    aspek = models.CharField(max_length=150, default="Kokurikuler", verbose_name="Aspek / Dimensi Pembiasaan")
    nilai_angka = models.FloatField(default=0, verbose_name="Rata-rata Nilai Kokurikuler")
    tp_scores = models.JSONField(default=dict, blank=True, verbose_name="Nilai TP 1-7 (JSON)")
    predikat = models.CharField(max_length=2, choices=PREDIKAT_CHOICES, default='A', verbose_name="Predikat")
    deskripsi = models.TextField(verbose_name="Deskripsi Capaian Karakter & Pembiasaan Murid")

    class Meta:
        verbose_name = "Nilai Kokurikuler"
        verbose_name_plural = "Nilai Kokurikuler"
        unique_together = ['anggota_kelas', 'semester', 'aspek']

    def __str__(self):
        return f"Kokurikuler: {self.anggota_kelas.murid.nama_lengkap} [{self.predikat}]"


class EkstrakurikulerNilai(models.Model):
    """
    Nilai Ekstrakurikuler Murid (maksimal 6 baris di dokumen rapor resmi).
    Contoh: Pramuka, Renang, Outbond, Lukis, Robotik, Panahan.
    """
    PREDIKAT_CHOICES = [
        ('A', 'Sangat Baik (A)'),
        ('B', 'Baik (B)'),
        ('C', 'Cukup (C)'),
        ('D', 'Kurang (D)'),
        ('-', '-'),
    ]

    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='nilai_ekskul_list')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='ekskul_list')
    kegiatan = models.CharField(max_length=150, verbose_name="Nama Kegiatan Ekstrakurikuler")
    predikat = models.CharField(max_length=5, choices=PREDIKAT_CHOICES, default='A', verbose_name="Predikat")
    keterangan = models.TextField(verbose_name="Keterangan Capaian Kegiatan")
    urutan = models.IntegerField(default=1, verbose_name="Nomor Baris (1-6)")

    class Meta:
        verbose_name = "Nilai Ekstrakurikuler"
        verbose_name_plural = "Nilai Ekstrakurikuler"
        unique_together = ['anggota_kelas', 'semester', 'urutan']
        ordering = ['urutan']

    def __str__(self):
        return f"{self.urutan}. {self.kegiatan} ({self.predikat}) - {self.anggota_kelas.murid.nama_lengkap}"


class PrestasiMurid(models.Model):
    """
    Data Prestasi & Penghargaan Murid (maksimal 6 baris di dokumen rapor resmi).
    Contoh: Kangaroo Math Contest, MHQ Tahfidz, Mewarnai Kaligrafi, dsb.
    """
    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='prestasi_list')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='prestasi_list')
    jenis_prestasi = models.CharField(max_length=255, verbose_name="Nama Kejuaraan / Jenis Prestasi")
    keterangan = models.TextField(verbose_name="Keterangan / Tingkat / Capaian Juara")
    urutan = models.IntegerField(default=1, verbose_name="Nomor Baris (1-6)")

    class Meta:
        verbose_name = "Prestasi Murid"
        verbose_name_plural = "Prestasi Murid"
        unique_together = ['anggota_kelas', 'semester', 'urutan']
        ordering = ['urutan']

    def __str__(self):
        return f"{self.urutan}. {self.jenis_prestasi} - {self.anggota_kelas.murid.nama_lengkap}"


class Ketidakhadiran(models.Model):
    """
    Rekapitulasi Presensi Murid (Sakit, Izin, Tanpa Keterangan).
    Tampil pada Halaman 6 mendampingi Titimangsa dan Tanda Tangan.
    """
    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='rekap_absen')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='absensi_list')
    sakit = models.IntegerField(default=0, verbose_name="Sakit (hari)")
    izin = models.IntegerField(default=0, verbose_name="Izin (hari)")
    tanpa_keterangan = models.IntegerField(default=0, verbose_name="Tanpa Keterangan (hari)")

    class Meta:
        verbose_name = "Rekap Ketidakhadiran"
        verbose_name_plural = "Rekap Ketidakhadiran"
        unique_together = ['anggota_kelas', 'semester']

    def __str__(self):
        return f"Absen {self.anggota_kelas.murid.nama_lengkap} (S:{self.sakit}, I:{self.izin}, A:{self.tanpa_keterangan})"


class CatatanWaliKelas(models.Model):
    """
    Catatan Naratif Wali Kelas (Boks Narasi Rata Justify).
    Dapat digenerate otomatis menggunakan Local AI (Ollama Qwen2.5) dan disunting manual.
    """
    anggota_kelas = models.ForeignKey(AnggotaKelas, on_delete=models.CASCADE, related_name='catatan_wali')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='catatan_wali_list')
    catatan = models.TextField(
        verbose_name="Isi Narasi Catatan Wali Kelas",
        help_text="Narasi motivatif, solutif, dan apresiatif islami perkembangan murid."
    )
    is_generated_by_ai = models.BooleanField(default=False, verbose_name="Dibuat oleh Asisten AI")
    ai_prompt_history = models.TextField(blank=True, verbose_name="Riwayat Prompt AI")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catatan Wali Kelas"
        verbose_name_plural = "Catatan Wali Kelas"
        unique_together = ['anggota_kelas', 'semester']

    def __str__(self):
        return f"Catatan Wali: {self.anggota_kelas.murid.nama_lengkap}"
