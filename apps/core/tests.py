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
