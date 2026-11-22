from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.kurikulum.models import MataPelajaran, KKTPRentang, TujuanPembelajaran, PembelajaranKelas
from apps.penilaian.models import NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
from apps.penilaian.services import get_kktp_and_predikat, generate_capaian_kompetensi

class PenilaianTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sekolah = Sekolah.objects.create(
            nama="SDIT Luqman Al Hakim Sleman",
            npsn="20409999",
            alamat="Jl. Palagan KM 10",
            kabupaten_kota="Sleman"
        )
        self.user = User.objects.create_superuser(username='wali_test', password='password123')
        self.pendidik = Pendidik.objects.create(
            user=self.user,
            nama_lengkap="Ustadz Wali Kelas",
            role="WALI_KELAS"
        )
        self.ta = TahunAjaran.objects.create(
            nama="2026/2027",
            tanggal_mulai="2026-07-01",
            tanggal_selesai="2027-06-30",
            is_active=True
        )
        self.sem = Semester.objects.create(
            tahun_ajaran=self.ta,
            semester=1,
            titimangsa_tanggal="2026-12-18",
            is_active=True
        )
        self.fase_a = Fase.objects.create(kode="A", nama="Fase A (Kelas 1 - 2)")
        self.kelas_1 = Kelas.objects.create(
            tahun_ajaran=self.ta,
            fase=self.fase_a,
            tingkat=1,
            nama="1 Bilal bin Rabah",
            wali_kelas=self.pendidik
        )
        self.murid = Murid.objects.create(
            nama_lengkap="Muhammad Arhan Al-Fatih",
            nis="2601001",
            nisn="0151234567",
            jenis_kelamin="L",
            tempat_lahir="Sleman",
            tanggal_lahir="2019-05-12",
            alamat_lengkap="Jl. Palagan KM 10"
        )
        self.anggota = AnggotaKelas.objects.create(
            kelas=self.kelas_1,
            murid=self.murid,
            nomor_absen=1
        )
        self.mupel = MataPelajaran.objects.create(
            kode="MTK",
            nama="Matematika",
            kategori="UMUM",
            urutan=4
        )
        self.kktp_a = KKTPRentang.objects.create(
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
        self.pembelajaran = PembelajaranKelas.objects.create(
            kelas=self.kelas_1,
            mata_pelajaran=self.mupel,
            guru_pengampu=self.pendidik,
            semester=self.sem
        )
        self.client.login(username='wali_test', password='password123')

    def test_kktp_service_calculation(self):
        pred, kktp = get_kktp_and_predikat(89.5, self.mupel, self.fase_a)
        self.assertEqual(pred, 'A')
        self.assertIsNotNone(kktp)

    def test_generate_capaian_kompetensi_service(self):
        pred, tertinggi, perlu = generate_capaian_kompetensi(
            89.0, self.mupel, self.fase_a, semester=1, tingkat=1
        )
        self.assertEqual(pred, 'A')
        self.assertIn("Murid menunjukkan penguasaan yang sangat baik dalam", tertinggi)
        self.assertIn("membilang cacah bilangan", tertinggi.lower())

    def test_nilai_matrix_view(self):
        response = self.client.get(reverse('nilai_matrix') + f"?kelas={self.kelas_1.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 Bilal bin Rabah")
        self.assertContains(response, "Matematika")

    def test_nilai_mupel_input_view(self):
        response = self.client.get(reverse('nilai_mupel_input', kwargs={'pembelajaran_id': self.pembelajaran.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")

    def test_kokurikuler_input_view(self):
        response = self.client.get(reverse('kokurikuler_input', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")

    def test_rekap_absen_input_view(self):
        response = self.client.get(reverse('rekap_absen_input', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")

    def test_matrix_tp_post_and_save(self):
        url = reverse('nilai_mupel_input', kwargs={'pembelajaran_id': self.pembelajaran.id})
        post_data = {
            'action': 'save',
            f'murid_{self.anggota.id}_tp_1': '90',
            f'murid_{self.anggota.id}_tp_2': '80',
            f'murid_{self.anggota.id}_tp_3': '85',
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        nilai = NilaiAkhir.objects.get(anggota_kelas=self.anggota, pembelajaran_kelas=self.pembelajaran)
        self.assertEqual(float(nilai.nilai_angka), 85.0)
        self.assertEqual(nilai.nilai_tp.get('1'), 90.0)
        self.assertEqual(nilai.nilai_tp.get('2'), 80.0)
        self.assertEqual(nilai.nilai_tp.get('3'), 85.0)
        self.assertTrue(nilai.capaian_tertinggi.startswith("Murid"))
        self.assertTrue(len(nilai.capaian_perlu_bimbingan) > 0)

    def test_api_generate_capaian_ai(self):
        url = reverse('api_generate_capaian_ai')
        payload = {
            'pembelajaran_id': self.pembelajaran.id,
            'anggota_id': self.anggota.id,
            'tp_scores': {'1': 95, '2': 70}
        }
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        res_json = response.json()
        self.assertEqual(res_json['status'], 'success')
        self.assertIn('tertinggi', res_json)
        self.assertIn('perlu', res_json)
        self.assertEqual(res_json['max_tp'], 1)
        self.assertEqual(res_json['min_tp'], 2)
