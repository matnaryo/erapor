from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.penilaian.models import CatatanWaliKelas
from .ollama_client import generate_wali_kelas_note, OLLAMA_MODEL

class AIAssistantTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sekolah = Sekolah.objects.create(
            nama="SDIT Luqman Al Hakim Sleman",
            npsn="20409999",
            alamat="Jl. Palagan KM 10",
            kabupaten_kota="Sleman"
        )
        self.user = User.objects.create_superuser(username='wali_ai_test', password='password123')
        self.pendidik = Pendidik.objects.create(
            user=self.user,
            nama_lengkap="Ustadz Wali AI",
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
        self.fase_b = Fase.objects.create(kode="B", nama="Fase B (Kelas 3 - 4)")
        self.kelas_1 = Kelas.objects.create(
            tahun_ajaran=self.ta,
            fase=self.fase_a,
            tingkat=1,
            nama="1 Bilal bin Rabah",
            wali_kelas=self.pendidik
        )
        self.kelas_2 = Kelas.objects.create(
            tahun_ajaran=self.ta,
            fase=self.fase_b,
            tingkat=2,
            nama="2C Abu Bakar Ash-Shiddiq",
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
        self.murid_2 = Murid.objects.create(
            nama_lengkap="Hilwa Sahara",
            nis="2602001",
            nisn="0151234568",
            jenis_kelamin="P",
            tempat_lahir="Sleman",
            tanggal_lahir="2018-03-20",
            alamat_lengkap="Jl. Kaliurang KM 9"
        )
        self.anggota = AnggotaKelas.objects.create(
            kelas=self.kelas_1,
            murid=self.murid,
            nomor_absen=1
        )
        self.anggota_2 = AnggotaKelas.objects.create(
            kelas=self.kelas_2,
            murid=self.murid_2,
            nomor_absen=1
        )
        self.client.login(username='wali_ai_test', password='password123')

    def test_ollama_generator_reads_grades_and_gives_recommendations(self):
        daftar_nilai = [
            {'nama': 'Pendidikan Agama Islam', 'nilai': 85.0, 'perlu': 'Makharijul huruf surat juz 30'},
            {'nama': 'Matematika', 'nilai': 89.0, 'tertinggi': 'Membilang cacah bilangan'}
        ]
        text, is_ai, prompt = generate_wali_kelas_note(
            nama_murid="Muhammad Arhan Al-Fatih",
            daftar_nilai=daftar_nilai,
            rata_rata=87.0,
            mupel_unggul=['Matematika (89)'],
            mupel_perlu_bimbingan=['Pendidikan Agama Islam (85)'],
            kokurikuler="Sangat baik sholat dhuha dan tahfidz",
            timeout=2
        )
        self.assertIsNotNone(text)
        self.assertTrue(len(text) > 20)
        self.assertIn("Alhamd", text)
        self.assertIn("Barakallahu fiik", text)
        self.assertIn("Muhammad Arhan Al-Fatih", prompt)

    def test_ai_generate_notes_view_get(self):
        response = self.client.get(reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, OLLAMA_MODEL)

    def test_ai_generate_single_post(self):
        response = self.client.post(
            reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id}),
            {'action': 'generate_single', 'anggota_id': self.anggota.id}
        )
        self.assertEqual(response.status_code, 302)
        catatan = CatatanWaliKelas.objects.filter(anggota_kelas=self.anggota).first()
        self.assertIsNotNone(catatan)
        self.assertIn("Alhamd", catatan.catatan)

    def test_superadmin_sees_rombel_dropdown_and_can_switch_classes(self):
        # Sebagai superadmin, pada kelas 1 terlihat dropdown berisi kelas 1 dan 2
        self.pendidik.role = 'SUPERADMIN'
        self.pendidik.save()
        self.user.refresh_from_db()
        self.client.force_login(self.user)
        response = self.client.get(reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pilih Rombel:")
        self.assertContains(response, "1 Bilal bin Rabah")
        self.assertContains(response, "2C Abu Bakar Ash-Shiddiq")
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertNotContains(response, "Hilwa Sahara")

        # Pindah ke kelas 2 via query param ?kelas=
        switch_response = self.client.get(f"{reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id})}?kelas={self.kelas_2.id}")
        self.assertRedirects(switch_response, reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_2.id}))

        # Halaman kelas 2 memuat murid kelas 2
        response_k2 = self.client.get(reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_2.id}))
        self.assertEqual(response_k2.status_code, 200)
        self.assertContains(response_k2, "Hilwa Sahara")
        self.assertNotContains(response_k2, "Muhammad Arhan Al-Fatih")

    def test_wali_kelas_does_not_see_rombel_dropdown(self):
        # Sebagai wali kelas murni, dropdown pilihan rombel disembunyikan
        self.pendidik.role = 'WALI_KELAS'
        self.pendidik.save()
        self.user.refresh_from_db()
        response = self.client.get(reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pilih Rombel:")

    def test_ai_generate_default_redirects_to_first_class(self):
        response = self.client.get(reverse('ai_generate_notes_default'))
        self.assertRedirects(response, reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id}))
