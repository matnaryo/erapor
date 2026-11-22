from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Sekolah, Pendidik
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.kurikulum.models import MataPelajaran, PembelajaranKelas
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
        self.assertIn('Mata Pelajaran', html)
        self.assertIn('Tujuan Pembelajaran (TP)', html)
        self.assertIn('Matriks Nilai Rapor', html)

        # 2. Cek proteksi akses URL langsung
        self.assertEqual(self.client.get(reverse('kelas_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('murid_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('kokurikuler_input', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
        self.assertEqual(self.client.get(reverse('rekap_absen_input', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
        self.assertEqual(self.client.get(reverse('catatan_wali_input', kwargs={'kelas_id': self.kelas.id})).status_code, 302)
        self.assertEqual(self.client.get(reverse('class_print_list', kwargs={'kelas_id': self.kelas.id})).status_code, 302)

    def test_guru_mapel_only_sees_assigned_mupel(self):
        user_mapel = User.objects.create_user(username='guru_mtk', password='password123')
        pendidik_mapel = Pendidik.objects.create(
            user=user_mapel,
            nama_lengkap='Guru Matematika, S.Pd.',
            role='GURU_MAPEL'
        )
        mupel_mtk = MataPelajaran.objects.create(kode='MTK', nama='Matematika', urutan=4, kategori='UMUM')
        mupel_pkn = MataPelajaran.objects.create(kode='PKN', nama='Pendidikan Pancasila', urutan=2, kategori='UMUM')
        
        pem_mtk = PembelajaranKelas.objects.create(
            kelas=self.kelas,
            mata_pelajaran=mupel_mtk,
            guru_pengampu=pendidik_mapel,
            semester=self.sem
        )
        pem_pkn = PembelajaranKelas.objects.create(
            kelas=self.kelas,
            mata_pelajaran=mupel_pkn,
            guru_pengampu=self.pendidik,
            semester=self.sem
        )

        self.client.login(username='guru_mtk', password='password123')

        # 1. Pada halaman Mata Pelajaran (mupel_list), hanya mupel yang diampu (MTK) yang tampil
        res_mupel = self.client.get(reverse('mupel_list'))
        self.assertEqual(res_mupel.status_code, 200)
        self.assertContains(res_mupel, 'Matematika')
        self.assertNotContains(res_mupel, 'Pendidikan Pancasila')

        # 2. Pada halaman TP (tp_list), dropdown mupel hanya berisi mupel yang diampu
        res_tp = self.client.get(reverse('tp_list'))
        self.assertEqual(res_tp.status_code, 200)
        tp_mupel_list = list(res_tp.context['mupel_list'])
        self.assertIn(mupel_mtk, tp_mupel_list)
        self.assertNotIn(mupel_pkn, tp_mupel_list)

        # 3. Pada halaman Matriks Nilai (nilai_matrix), hanya jadwal pembelajaran MTK yang muncul
        res_matrix = self.client.get(reverse('nilai_matrix'))
        self.assertEqual(res_matrix.status_code, 200)
        matrix_pem_list = list(res_matrix.context['pembelajaran_list'])
        self.assertIn(pem_mtk, matrix_pem_list)
        self.assertNotIn(pem_pkn, matrix_pem_list)

        # 4. Guru mapel tidak boleh mengakses input nilai mupel yang tidak diampunya
        res_input_pkn = self.client.get(reverse('nilai_mupel_input', kwargs={'pembelajaran_id': pem_pkn.id}))
        self.assertEqual(res_input_pkn.status_code, 302)
