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
        self.assertContains(response, "Kelas 1")

    def test_tp_filter_by_tingkat(self):
        # Buat TP untuk Kelas 2
        tp2 = TujuanPembelajaran.objects.create(
            mata_pelajaran=self.mupel,
            fase=self.fase_a,
            tingkat=2,
            semester=1,
            kode="TP 2.1",
            deskripsi="Menyelesaikan perkalian dan pembagian dasar.",
            urutan=1
        )
        # Filter spesifik Kelas 2
        url = reverse('tp_list') + f"?mupel={self.mupel.id}&tingkat=2&sem=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TP 2.1")
        self.assertContains(response, "Menyelesaikan perkalian dan pembagian dasar")

    def test_tp_add_edit_delete(self):
        # 1. Tambah TP baru via POST
        url = reverse('tp_list')
        add_data = {
            'action': 'add',
            'mupel_id': self.mupel.id,
            'tingkat': '2',
            'sem': '1',
            'kode': 'TP 2.2',
            'urutan': '2',
            'deskripsi': 'Mengenal pecahan sederhana seperdua dan seperempat.'
        }
        res_add = self.client.post(url, add_data, follow=True)
        self.assertEqual(res_add.status_code, 200)
        tp_baru = TujuanPembelajaran.objects.filter(kode='TP 2.2').first()
        self.assertIsNotNone(tp_baru)
        self.assertEqual(tp_baru.tingkat, 2)
        self.assertEqual(tp_baru.fase.kode, 'A')

        # 2. Edit TP via POST
        edit_data = {
            'action': 'edit',
            'tp_id': tp_baru.id,
            'tingkat': '2',
            'kode': 'TP 2.2 Revisi',
            'urutan': '3',
            'deskripsi': 'Deskripsi TP 2.2 telah disunting oleh guru mapel.'
        }
        res_edit = self.client.post(url, edit_data, follow=True)
        self.assertEqual(res_edit.status_code, 200)
        tp_baru.refresh_from_db()
        self.assertEqual(tp_baru.kode, 'TP 2.2 Revisi')
        self.assertEqual(tp_baru.urutan, 3)
        self.assertIn('disunting', tp_baru.deskripsi)

        # 3. Hapus TP via POST
        del_data = {
            'action': 'delete',
            'tp_id': tp_baru.id
        }
        res_del = self.client.post(url, del_data, follow=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(TujuanPembelajaran.objects.filter(id=tp_baru.id).exists())
