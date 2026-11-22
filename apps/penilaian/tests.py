from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.kurikulum.models import MataPelajaran, KKTPRentang, TujuanPembelajaran, PembelajaranKelas
from apps.penilaian.models import NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
from apps.penilaian.services import get_kktp_and_predikat, generate_capaian_kompetensi, get_tp_descriptions

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

    def test_ekskul_prestasi_kelas_view(self):
        url = reverse('ekskul_prestasi_kelas', kwargs={'kelas_id': self.kelas_1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "1 Bilal bin Rabah")
        self.assertContains(response, "Ekstrakurikuler & Prestasi")

    def test_prestasi_matrix_view(self):
        url = reverse('prestasi_matrix_kelas', kwargs={'kelas_id': self.kelas_1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "Matriks Prestasi Murid")

        post_data = {
            f'murid_{self.anggota.id}_prestasi_1_jenis': 'Juara 1 MTQ',
            f'murid_{self.anggota.id}_prestasi_1_keterangan': 'Tingkat Kabupaten Sleman',
        }
        res_post = self.client.post(url, post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)
        p = PrestasiMurid.objects.get(anggota_kelas=self.anggota, urutan=1)
        self.assertEqual(p.jenis_prestasi, 'Juara 1 MTQ')
        self.assertEqual(p.keterangan, 'Tingkat Kabupaten Sleman')

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

    def test_ekskul_matrix_get_and_post(self):
        url = reverse('ekskul_matrix_kelas', kwargs={'kelas_id': self.kelas_1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "Ekstrakurikuler 1")
        self.assertContains(response, "Ekstrakurikuler 6")

        # POST input ekskul
        post_data = {
            f'murid_{self.anggota.id}_ekskul_1_kegiatan': 'Pramuka Siaga',
            f'murid_{self.anggota.id}_ekskul_1_predikat': 'A',
            f'murid_{self.anggota.id}_ekskul_1_keterangan': 'Sangat aktif dalam kegiatan kepanduan.',
            f'murid_{self.anggota.id}_ekskul_2_kegiatan': 'Panahan',
            f'murid_{self.anggota.id}_ekskul_2_predikat': 'B',
            f'murid_{self.anggota.id}_ekskul_2_keterangan': 'Fokus membidik sasaran dengan baik.',
        }
        res_post = self.client.post(url, post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)

        ekskuls = EkstrakurikulerNilai.objects.filter(anggota_kelas=self.anggota).order_by('urutan')
        self.assertEqual(ekskuls.count(), 2)
        self.assertEqual(ekskuls[0].kegiatan, 'Pramuka Siaga')
        self.assertEqual(ekskuls[0].predikat, 'A')
        self.assertEqual(ekskuls[1].kegiatan, 'Panahan')

    def test_kokurikuler_matrix_get_and_post(self):
        url = reverse('kokurikuler_matrix_kelas', kwargs={'kelas_id': self.kelas_1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "TP 1")
        self.assertContains(response, "TP 7")
        self.assertContains(response, "Obs")
        self.assertContains(response, "Juri")

        # POST input nilai TP 1-7 skala 4 (Observasi & Juri)
        post_data = {
            f'murid_{self.anggota.id}_tp_1_obs': '3.6',
            f'murid_{self.anggota.id}_tp_1_juri': '3.4',
            f'murid_{self.anggota.id}_tp_2_obs': '3.0',
            f'murid_{self.anggota.id}_tp_2_juri': '3.0',
            f'murid_{self.anggota.id}_tp_3_obs': '3.8',
            f'murid_{self.anggota.id}_tp_3_juri': '3.8',
            f'murid_{self.anggota.id}_tp_4_obs': '3.5',
            f'murid_{self.anggota.id}_tp_4_juri': '3.5',
            f'murid_{self.anggota.id}_tp_5_obs': '3.2',
            f'murid_{self.anggota.id}_tp_5_juri': '3.2',
            f'murid_{self.anggota.id}_tp_6_obs': '3.7',
            f'murid_{self.anggota.id}_tp_6_juri': '3.7',
            f'murid_{self.anggota.id}_tp_7_obs': '3.5',
            f'murid_{self.anggota.id}_tp_7_juri': '3.5',
        }
        res_post = self.client.post(url, post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)

        koku = KokurikulerNilai.objects.get(anggota_kelas=self.anggota, semester=self.sem)
        self.assertGreaterEqual(koku.nilai_angka, 3.2)
        self.assertEqual(koku.predikat, 'A')
        self.assertEqual(koku.tp_scores.get('1'), 3.5)
        self.assertEqual(koku.tp_scores.get('1_obs'), 3.6)
        self.assertEqual(koku.tp_scores.get('1_juri'), 3.4)
        self.assertIn("sangat baik dalam", koku.deskripsi)
        self.assertIn("baik dalam", koku.deskripsi)

    def test_kokurikuler_tp_list_get_and_post(self):
        url = reverse('kokurikuler_tp_list') + "?tingkat=1&sem=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tujuan Pembelajaran Kokurikuler")

        post_data = {
            'tp_1_kode': 'TP 1',
            'tp_1_deskripsi': 'Membiasakan sholat dhuha berjamaah dan tartil hafalan.',
        }
        res_post = self.client.post(url, post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)

    def test_get_tp_descriptions_filtered_by_tingkat(self):
        # self.pembelajaran ada di kelas_1 (tingkat=1)
        # Buat TP untuk tingkat 1 dan tingkat 2 pada mupel yang sama
        TujuanPembelajaran.objects.create(
            mata_pelajaran=self.mupel,
            fase=self.fase_a,
            tingkat=2,
            semester=1,
            kode="TP 2.1",
            deskripsi="TP Khusus Kelas 2 yang tidak boleh bocor ke Kelas 1",
            urutan=1
        )
        tps = get_tp_descriptions(self.pembelajaran)
        # Pembelajaran kelas 1 harus mendapatkan TP milik tingkat 1
        self.assertIn(1, tps)
        self.assertEqual(tps[1], "Membilang cacah bilangan hingga 20 dan menyelesaikan operasi penjumlahan konkrit.")
        self.assertNotIn("Khusus Kelas 2", tps[1])
        # Pastikan tidak ada TP dummy tak terdefinisi (misal TP 15)
        self.assertNotIn(15, tps)

    def test_nilai_matrix_empty_tp_disabled(self):
        url = reverse('nilai_mupel_input', kwargs={'pembelajaran_id': self.pembelajaran.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Kolom TP 1 aktif
        self.assertContains(response, f'id="tp_{self.anggota.id}_1"')
        # Kolom yang tidak dirumuskan (misal TP 15) harus disabled
        self.assertContains(response, 'disabled readonly tabindex="-1"')
