from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Sekolah, Pendidik
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
import datetime

class AuthAndDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.sekolah = Sekolah.objects.create(
            nama="SD Islam Terpadu Luqman Al Hakim Sleman",
            npsn="20401127",
            titimangsa_default="Sleman"
        )
        self.user = User.objects.create_user(
            username='irsyad_wali',
            password='bismillah123',
            first_name='Muhammad Nur Irsyad'
        )
        self.pendidik = Pendidik.objects.create(
            user=self.user,
            nama_lengkap='Muhammad Nur Irsyad Maulana, S.Pd.',
            role='WALI_KELAS'
        )
        self.ta = TahunAjaran.objects.create(
            nama='2026/2027',
            tanggal_mulai=datetime.date(2026, 7, 1),
            tanggal_selesai=datetime.date(2027, 6, 30),
            is_active=True
        )
        self.sem = Semester.objects.create(
            tahun_ajaran=self.ta,
            semester=1,
            titimangsa_tanggal=datetime.date(2026, 12, 18),
            is_active=True
        )
        self.fase_a = Fase.objects.create(kode='A', nama='Fase A')
        self.kelas = Kelas.objects.create(
            tahun_ajaran=self.ta,
            fase=self.fase_a,
            tingkat=1,
            nama='I',
            wali_kelas=self.pendidik
        )

    def test_login_page_renders_cleanly(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'e-Rapor eLHaEs')
        self.assertContains(response, 'SD Islam Terpadu Luqman Al Hakim Sleman')

    def test_login_success_and_dashboard_access(self):
        login_response = self.client.post(reverse('login'), {
            'username': 'irsyad_wali',
            'password': 'bismillah123'
        }, follow=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Ahlan wa Sahlan')
        self.assertContains(login_response, 'Wali Kelas')
        self.assertContains(login_response, 'Kelas I')

    def test_unauthenticated_dashboard_redirects_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_logout(self):
        self.client.login(username='irsyad_wali', password='bismillah123')
        response = self.client.get(reverse('logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anda telah keluar')

    def test_guru_mapel_menu_and_access_restrictions(self):
        user_mapel = User.objects.create_user(
            username='guru_mapel',
            password='password123',
            first_name='Ustadz Mapel'
        )
        Pendidik.objects.create(
            user=user_mapel,
            nama_lengkap='Ustadz Mapel, S.Pd.',
            role='GURU_MAPEL'
        )
        self.client.login(username='guru_mapel', password='password123')
        
        # 1. Cek tampilan sidebar navigasi
        dash_res = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.content.decode('utf-8')
        
        # Menu yang WAJIB disembunyikan untuk Guru Mapel
        self.assertNotIn('Tugas Khusus Wali Kelas', html)
        self.assertNotIn('Pusat Cetak Dokumen', html)
        self.assertNotIn('Buku Induk Murid', html)
        self.assertNotIn('Rombel / Kelas (1-6)', html)
        
        # Menu yang WAJIB tampil untuk Guru Mapel
        self.assertIn('11 Mata Pelajaran', html)
        self.assertIn('Tujuan Pembelajaran (TP)', html)
        self.assertIn('Matriks Nilai Rapor', html)

        # 2. Cek proteksi akses URL langsung
        self.assertEqual(self.client.get(reverse('kelas_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('murid_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('kokurikuler_input', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
        self.assertEqual(self.client.get(reverse('rekap_absen_input', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
        self.assertEqual(self.client.get(reverse('catatan_wali_input', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
        self.assertEqual(self.client.get(reverse('class_print_list', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
