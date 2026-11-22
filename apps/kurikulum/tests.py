from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from apps.master_akademik.models import Fase
from .models import MataPelajaran, KKTPRentang, TujuanPembelajaran

class KurikulumTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sekolah = Sekolah.objects.create(
            nama="SDIT Luqman Al Hakim Sleman",
            npsn="20409999",
            alamat="Jl. Palagan KM 10",
            kabupaten_kota="Sleman"
        )
        self.user = User.objects.create_superuser(username='admin_kurikulum', password='password123')
        self.pendidik = Pendidik.objects.create(
            user=self.user,
            nama_lengkap="Ustadz Kurikulum",
            role="KURIKULUM"
        )
        self.fase_a = Fase.objects.create(kode="A", nama="Fase A (Kelas 1 - 2)")
        self.mupel = MataPelajaran.objects.create(
            kode="MTK",
            nama="Matematika",
            kategori="UMUM",
            urutan=4
        )
        self.kktp = KKTPRentang.objects.create(
            mata_pelajaran=self.mupel,
            fase=self.fase_a,
            predikat="A",
            label="Sangat Baik",
            nilai_min=88.0,
            nilai_max=100.0,
            keterangan_default="Murid menunjukkan penguasaan yang sangat baik dalam"
        )
        self.tp = TujuanPembelajaran.objects.create(
            mata_pelajaran=self.mupel,
            fase=self.fase_a,
            tingkat=1,
            semester=1,
            kode="TP 1.1",
            deskripsi="Membilang cacah bilangan hingga 20 dan menyelesaikan operasi penjumlahan konkrit.",
            urutan=1
        )
        self.client.login(username='admin_kurikulum', password='password123')

    def test_mupel_list_view(self):
        response = self.client.get(reverse('mupel_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Matematika")
        self.assertContains(response, "MTK")

    def test_kktp_manage_view_get(self):
        response = self.client.get(reverse('kktp_manage') + f"?mupel={self.mupel.id}&fase=A")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sangat Baik")
        self.assertContains(response, "kktp_")

    def test_tp_list_view_get(self):
        response = self.client.get(reverse('tp_list') + f"?mupel={self.mupel.id}&fase=A&sem=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TP 1.1")
        self.assertContains(response, "Membilang cacah bilangan hingga 20")
