from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from .models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas

class MasterAkademikTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sekolah = Sekolah.objects.create(
            nama="SDIT Luqman Al Hakim Sleman",
            npsn="20409999",
            alamat="Jl. Palagan KM 10",
            kabupaten_kota="Sleman",
            kepala_sekolah_nama="Arif Rahman Hakim, M.Pd.",
            kepala_sekolah_nip="198207152006041008"
        )
        self.user = User.objects.create_user(username='guru_test', password='password123')
        self.pendidik = Pendidik.objects.create(
            user=self.user,
            nama_lengkap="Ustadz Test, S.Pd.",
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
            agama="Islam",
            nama_ayah="Fatih Abdullah",
            nama_ibu="Siti Sarah",
            pekerjaan_ayah="Wiraswasta",
            pekerjaan_ibu="Guru",
            alamat_lengkap="Jl. Palagan Tentara Pelajar No. 45"
        )
        self.anggota = AnggotaKelas.objects.create(
            kelas=self.kelas_1,
            murid=self.murid,
            nomor_absen=1
        )
        self.client.login(username='guru_test', password='password123')

    def test_murid_list_view(self):
        response = self.client.get(reverse('murid_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")

    def test_murid_detail_view(self):
        response = self.client.get(reverse('murid_detail', kwargs={'pk': self.murid.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0151234567")
        self.assertContains(response, "1 Bilal bin Rabah")

    def test_kelas_list_view(self):
        response = self.client.get(reverse('kelas_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 Bilal bin Rabah")
        self.assertContains(response, "Ustadz Test, S.Pd.")

    def test_kelas_anggota_view(self):
        response = self.client.get(reverse('kelas_anggota', kwargs={'pk': self.kelas_1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "1 Bilal bin Rabah")

    def test_tambah_anggota_kelas(self):
        murid_2 = Murid.objects.create(
            nama_lengkap="Haidar Zakaria",
            nis="2601002",
            nisn="0151234568",
            jenis_kelamin="L",
            tempat_lahir="Sleman",
            tanggal_lahir="2019-06-15",
            agama="Islam",
            alamat_lengkap="Jl. Palagan KM 11"
        )
        response = self.client.post(reverse('kelas_anggota', kwargs={'pk': self.kelas_1.pk}), {
            'action': 'tambah',
            'murid_id': murid_2.pk,
            'nomor_absen': 2
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AnggotaKelas.objects.filter(kelas=self.kelas_1, murid=murid_2, nomor_absen=2).exists())

    def test_hapus_anggota_kelas(self):
        response = self.client.post(reverse('kelas_hapus_anggota', kwargs={
            'kelas_id': self.kelas_1.pk,
            'anggota_id': self.anggota.pk
        }), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AnggotaKelas.objects.filter(pk=self.anggota.pk).exists())

    def test_murid_tempatkan_kelas_view(self):
        murid_3 = Murid.objects.create(
            nama_lengkap="Aisyah Humaira",
            nis="2601003",
            nisn="0151234569",
            jenis_kelamin="P",
            tempat_lahir="Yogyakarta",
            tanggal_lahir="2019-07-20",
            agama="Islam",
            alamat_lengkap="Jl. Kaliurang KM 9"
        )
        response = self.client.post(reverse('murid_tempatkan_kelas', kwargs={'pk': murid_3.pk}), {
            'kelas_id': self.kelas_1.pk,
            'nomor_absen': 3
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AnggotaKelas.objects.filter(kelas=self.kelas_1, murid=murid_3, nomor_absen=3).exists())
