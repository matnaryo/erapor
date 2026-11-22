from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.penilaian.models import CatatanWaliKelas
from .ollama_client import generate_wali_kelas_note

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
        self.client.login(username='wali_ai_test', password='password123')

    def test_ollama_generator_fallback_or_live(self):
        text, is_ai, prompt = generate_wali_kelas_note(
            nama_murid="Muhammad Arhan Al-Fatih",
            nilai_summary="Matematika 89, PAI 92",
            kokurikuler="Sangat baik sholat dhuha dan tahfidz"
        )
        self.assertIsNotNone(text)
        self.assertTrue(len(text) > 20)
        self.assertIn("Alhamd", text)

    def test_ai_generate_notes_view_get(self):
        response = self.client.get(reverse('ai_generate_notes_kelas', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "Ollama")
