from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.core.models import Pendidik, Sekolah
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.kurikulum.models import MataPelajaran, PembelajaranKelas
from apps.penilaian.models import NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, PrestasiMurid, Ketidakhadiran, CatatanWaliKelas

class PrintingTests(TestCase):
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
        self.user = User.objects.create_superuser(username='print_admin', password='password123')
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
        self.client.login(username='print_admin', password='password123')

    def test_class_print_list_view(self):
        response = self.client.get(reverse('class_print_list', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "Cetak Rapor (6 Hal)")

    def test_class_print_default_redirects_to_first_class(self):
        response = self.client.get(reverse('class_print_default'))
        self.assertRedirects(response, reverse('class_print_list', kwargs={'kelas_id': self.kelas_1.id}))

    def test_superadmin_sees_class_dropdown_and_can_switch_classes(self):
        # Promosikan pendidik ke SUPERADMIN
        self.pendidik.role = 'SUPERADMIN'
        self.pendidik.save()
        self.user.refresh_from_db()
        self.client.force_login(self.user)

        # Buat kelas ke-2 dengan murid
        kelas_2 = Kelas.objects.create(
            tahun_ajaran=self.ta,
            fase=self.fase_a,
            tingkat=2,
            nama="2 Umar bin Khattab"
        )
        murid_2 = Murid.objects.create(
            nama_lengkap="Fatimah Az-Zahra",
            nis="2601002",
            nisn="0151234568",
            jenis_kelamin="P",
            tanggal_lahir="2018-03-15"
        )
        AnggotaKelas.objects.create(
            kelas=kelas_2,
            murid=murid_2,
            nomor_absen=1
        )

        # Akses halaman kelas 1
        response = self.client.get(reverse('class_print_list', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_admin'])
        self.assertContains(response, "Pilih Rombel:")
        self.assertContains(response, "2 Umar bin Khattab")

        # Pindah kelas via parameter ?kelas=
        switch_url = f"{reverse('class_print_list', kwargs={'kelas_id': self.kelas_1.id})}?kelas={kelas_2.id}"
        response_switch = self.client.get(switch_url)
        self.assertRedirects(response_switch, reverse('class_print_list', kwargs={'kelas_id': kelas_2.id}))

        # Akses langsung kelas 2 menampilkan murid kelas 2
        response_k2 = self.client.get(reverse('class_print_list', kwargs={'kelas_id': kelas_2.id}))
        self.assertEqual(response_k2.status_code, 200)
        self.assertContains(response_k2, "Fatimah Az-Zahra")

    def test_wali_kelas_locked_to_own_class_in_print(self):
        # Buat kelas lain tanpa akses wali kelas saat ini
        kelas_lain = Kelas.objects.create(
            tahun_ajaran=self.ta,
            fase=self.fase_a,
            tingkat=2,
            nama="2 Ali bin Abi Thalib"
        )

        # Wali kelas mengakses kelasnya sendiri -> berhasil
        response = self.client.get(reverse('class_print_list', kwargs={'kelas_id': self.kelas_1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_admin'])
        # Dropdown ganti kelas tidak boleh muncul untuk wali kelas
        self.assertNotContains(response, "Pilih Rombel:")

        # Wali kelas mencoba mengakses kelas lain -> dilarang dan diarahkan ke dashboard
        response_lain = self.client.get(reverse('class_print_list', kwargs={'kelas_id': kelas_lain.id}))
        self.assertRedirects(response_lain, reverse('dashboard'))

    def test_rapor_print_view(self):
        response = self.client.get(reverse('rapor_print', kwargs={'anggota_id': self.anggota.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "Halaman 1 dari 6")
        self.assertContains(response, "Halaman 6 dari 6")

    def test_cover_print_view(self):
        response = self.client.get(reverse('cover_print', kwargs={'anggota_id': self.anggota.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muhammad Arhan Al-Fatih")
        self.assertContains(response, "RAPOR HASIL BELAJAR")
        self.assertContains(response, "IDENTITAS MURID")
