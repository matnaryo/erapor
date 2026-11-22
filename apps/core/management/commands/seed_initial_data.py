import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.core.models import Sekolah, Pendidik
from apps.master_akademik.models import TahunAjaran, Semester, Fase, Kelas, Murid, AnggotaKelas
from apps.kurikulum.models import MataPelajaran, KKTPRentang, PembelajaranKelas
from apps.penilaian.models import (
    NilaiAkhir, KokurikulerNilai, EkstrakurikulerNilai, 
    PrestasiMurid, Ketidakhadiran, CatatanWaliKelas
)

class Command(BaseCommand):
    help = 'Seed initial master data and sample report data for SDIT Luqman Al Hakim Sleman'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding for SDIT Luqman Al Hakim Sleman..."))

        # 1. Profil Sekolah
        sekolah, _ = Sekolah.objects.get_or_create(
            id=1,
            defaults={
                'nama': "SD Islam Terpadu Luqman Al Hakim Sleman",
                'npsn': "20401127",
                'nss': "102040206001",
                'alamat': "Jl. Palagan Tentara Pelajar No. 52 Sedan, Sariharjo, Ngaglik, Sleman, D.I. Yogyakarta 55581",
                'desa_kelurahan': "Sariharjo",
                'kecamatan': "Ngaglik",
                'kabupaten_kota': "Sleman",
                'provinsi': "D.I. Yogyakarta",
                'kode_pos': "55581",
                'titimangsa_default': "Sleman",
                'kepala_sekolah_nama': "Ahmad Sholihin, S.Pd.I.",
                'kepala_sekolah_nip': "19780815 200501 1 003"
            }
        )
        self.stdout.write(f"- Profil Sekolah: {sekolah.nama}")

        # 2. Fase Kurikulum Merdeka
        fase_a, _ = Fase.objects.get_or_create(kode='A', defaults={'nama': 'Fase A (Kelas 1 - 2)'})
        fase_b, _ = Fase.objects.get_or_create(kode='B', defaults={'nama': 'Fase B (Kelas 3 - 4)'})
        fase_c, _ = Fase.objects.get_or_create(kode='C', defaults={'nama': 'Fase C (Kelas 5 - 6)'})
        self.stdout.write("- Fase A, B, C created")

        # 3. Tahun Ajaran & Semester
        ta, _ = TahunAjaran.objects.get_or_create(
            nama="2026/2027",
            defaults={
                'tanggal_mulai': datetime.date(2026, 7, 15),
                'tanggal_selesai': datetime.date(2027, 6, 20),
                'is_active': True
            }
        )
        sem1, _ = Semester.objects.get_or_create(
            tahun_ajaran=ta,
            semester=1,
            defaults={
                'titimangsa_tanggal': datetime.date(2026, 12, 18),
                'titimangsa_tempat': 'Sleman',
                'is_active': True
            }
        )
        self.stdout.write(f"- Tahun Ajaran {ta.nama} & Semester {sem1.semester} created")

        # 4. Akun Superadmin & Wali Kelas
        # 4a. Akun Superadmin Resmi (admin)
        user_admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Administrator',
                'last_name': 'eLHaEs',
                'email': 'admin@sdit-lhs.sch.id',
                'is_staff': True,
                'is_superuser': True
            }
        )
        user_admin.is_staff = True
        user_admin.is_superuser = True
        user_admin.set_password('bismillah123')
        user_admin.save()

        pendidik_admin, _ = Pendidik.objects.get_or_create(
            user=user_admin,
            defaults={
                'nama_lengkap': "Administrator eLHaEs (Superadmin)",
                'role': 'SUPERADMIN',
                'jenis_kelamin': 'L',
                'no_hp': '081200000001'
            }
        )
        pendidik_admin.role = 'SUPERADMIN'
        pendidik_admin.is_active = True
        pendidik_admin.save()
        self.stdout.write(f"- Superadmin 'admin': bismillah123")

        # 4b. Akun alias 'superuser' jika pengguna login dengan username superuser
        user_su, _ = User.objects.get_or_create(
            username='superuser',
            defaults={
                'first_name': 'Superuser',
                'last_name': 'eLHaEs',
                'email': 'superuser@sdit-lhs.sch.id',
                'is_staff': True,
                'is_superuser': True
            }
        )
        user_su.is_staff = True
        user_su.is_superuser = True
        user_su.set_password('bismillah123')
        user_su.save()

        pendidik_su, _ = Pendidik.objects.get_or_create(
            user=user_su,
            defaults={
                'nama_lengkap': "Superuser SDIT Luqman Al Hakim",
                'role': 'SUPERADMIN',
                'jenis_kelamin': 'L',
                'no_hp': '081200000002'
            }
        )
        pendidik_su.role = 'SUPERADMIN'
        pendidik_su.is_active = True
        pendidik_su.save()
        self.stdout.write(f"- Superadmin 'superuser': bismillah123")

        # 4c. Akun Wali Kelas I (irsyad_wali) - juga diberikan hak superuser agar tidak terhalang
        user_wali, _ = User.objects.get_or_create(
            username='irsyad_wali',
            defaults={
                'first_name': 'Muhammad Nur Irsyad',
                'last_name': 'Maulana',
                'email': 'irsyad@sdit-lhs.sch.id',
                'is_staff': True,
                'is_superuser': True
            }
        )
        user_wali.is_staff = True
        user_wali.is_superuser = True
        user_wali.set_password('bismillah123')
        user_wali.save()

        pendidik_wali, _ = Pendidik.objects.get_or_create(
            user=user_wali,
            defaults={
                'nama_lengkap': "Muhammad Nur Irsyad Maulana, S.Pd.",
                'niy': "1234567890",
                'role': 'WALI_KELAS',
                'jenis_kelamin': 'L',
                'no_hp': '081234567890'
            }
        )
        self.stdout.write(f"- Wali Kelas 'irsyad_wali': {pendidik_wali.nama_lengkap}")

        # 5. Rombel / Kelas I
        kelas_1, _ = Kelas.objects.get_or_create(
            tahun_ajaran=ta,
            nama="I",
            defaults={
                'fase': fase_a,
                'tingkat': 1,
                'wali_kelas': pendidik_wali
            }
        )
        self.stdout.write(f"- Kelas: {kelas_1.nama} (Wali: {pendidik_wali.nama_lengkap})")

        # 6. Master 11 Mata Pelajaran Resmi (Sesuai Urutan Rapor Baku)
        mupel_data = [
            ('PAI', 'Pendidikan Agama Islam dan Budi Pekerti', 'UMUM', 1),
            ('PP', 'Pendidikan Pancasila', 'UMUM', 2),
            ('BIN', 'Bahasa Indonesia', 'UMUM', 3),
            ('MTK', 'Matematika', 'UMUM', 4),
            ('IPAS', 'Ilmu Pengetahuan Alam dan Sosial', 'UMUM', 5),
            ('SR', 'Seni Rupa', 'UMUM', 6),
            ('PJOK', 'Pendidikan Jasmani, Olahraga, dan Kesehatan', 'UMUM', 7),
            ('BIG', 'Bahasa Inggris', 'UMUM', 8),
            ('KKA', 'Koding dan Kecerdasan Artifisial', 'PILIHAN', 9),
            ('BAR', 'Bahasa Arab', 'PILIHAN', 10),
            ('BJW', 'Bahasa Jawa', 'MULOK', 11),
        ]

        mupel_objects = {}
        for kode, nama, kategori, urut in mupel_data:
            m, _ = MataPelajaran.objects.get_or_create(
                kode=kode,
                defaults={
                    'nama': nama,
                    'kategori': kategori,
                    'urutan': urut,
                    'is_active': True
                }
            )
            mupel_objects[kode] = m

            # Setup KKTP Rentang Dinamis Default per Mupel
            for pred, label, n_min, n_max in [
                ('A', 'Sangat Baik', 88, 100),
                ('B', 'Baik', 75, 87),
                ('C', 'Cukup', 65, 74),
                ('D', 'Perlu Bimbingan', 0, 64),
            ]:
                KKTPRentang.objects.get_or_create(
                    mata_pelajaran=m,
                    fase=fase_a,
                    predikat=pred,
                    defaults={
                        'label': label,
                        'nilai_min': n_min,
                        'nilai_max': n_max,
                        'keterangan_default': f"Murid menunjukkan penguasaan yang {label.lower()}"
                    }
                )

            # Assign Pembelajaran Kelas
            PembelajaranKelas.objects.get_or_create(
                kelas=kelas_1,
                mata_pelajaran=m,
                semester=sem1,
                defaults={'guru_pengampu': pendidik_wali}
            )

        self.stdout.write("- 11 Mata Pelajaran Resmi, KKTP Dinamis, & Penugasan Kelas created")

        # 7. Data Murid Contoh (Arhan Bagas Chandra Diandra Eka Firman)
        murid, _ = Murid.objects.get_or_create(
            nisn="1234567890",
            defaults={
                'nis': "0123",
                'nama_lengkap': "ARHAN BAGAS CHANDRA DIANDRA EKA FIRMAN",
                'jenis_kelamin': 'L',
                'tempat_lahir': "Sleman",
                'tanggal_lahir': datetime.date(2018, 5, 12),
                'agama': "Islam",
                'pendidikan_sebelumnya': "TK IT Luqman Al Hakim",
                'alamat_lengkap': "Jl. Palagan Tentara Pelajar No. 52 Sedan, Sariharjo, Ngaglik, Sleman, D.I. Yogyakarta, 55581",
                'desa_kelurahan': "Sariharjo",
                'kecamatan': "Ngaglik",
                'kabupaten_kota': "Sleman",
                'provinsi': "D.I. Yogyakarta",
                'kode_pos': "55581",
                'nama_ayah': "Bambang Chandra",
                'pekerjaan_ayah': "Karyawan Swasta",
                'nama_ibu': "Dewi Anggraini",
                'pekerjaan_ibu': "Guru",
            }
        )

        anggota, _ = AnggotaKelas.objects.get_or_create(
            kelas=kelas_1,
            murid=murid,
            defaults={'nomor_absen': 1}
        )
        self.stdout.write(f"- Murid: {murid.nama_lengkap} (No Presensi: {anggota.nomor_absen})")

        # 8. Data Nilai Rapor Resmi Sample
        sample_nilai = [
            ('PAI', 85, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam memahami rukun Islam, menghafal doa harian, dan keteladanan akhlak Nabi Muhammad SAW.', 'Murid perlu bimbingan dalam melafalkan makharijul huruf dan tajwid dasar pada surat-surat pendek Juz 30.'),
            ('PP', 89, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam mengenal simbol sila-sila Pancasila dan penerapannya dalam kehidupan kelas.', 'Murid menunjukkan penguasaan yang cukup baik dalam mematuhi aturan kesepakatan bersama saat bermain dan belajar.'),
            ('BIN', 87, 'B', 'Murid menunjukkan penguasaan yang sangat baik dalam menyimak teks narasi sederhana, mengeja suku kata, dan memperkaya kosa kata baru.', 'Murid perlu bimbingan dalam menulis kalimat sederhana menggunakan huruf kapital dan tanda titik secara tepat.'),
            ('MTK', 89, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam membilang cacah bilangan hingga 20 dan menyelesaikan operasi penjumlahan konkrit.', 'Murid perlu bimbingan dalam mengelompokkan bentuk bangun datar bersudut dan mendeskripsikan polanya.'),
            ('IPAS', 88, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam mengenali bagian tubuh beserta fungsinya dan cara memelihara kesehatan diri.', 'Murid menunjukkan penguasaan yang baik dalam menceritakan silsilah keluarga inti dan denah lingkungan sekitar rumah.'),
            ('SR', 88, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam eksplorasi garis, bentuk geometris dasar, dan kepekaan memadukan gradasi warna cerah.', 'Murid menunjukkan penguasaan yang baik dalam merapikan alat lukis dan menjaga kebersihan bidang gambar mandiri.'),
            ('PJOK', 90, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam mempraktikkan keterampilan pola gerak dasar lokomotor jalan, lari, dan lompat.', 'Murid menunjukkan penguasaan yang baik dalam menjaga kebersihan kuku, tangan, dan pakaian setelah berolahraga.'),
            ('BIG', 89, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam merespon salam, perkenalan diri, dan instruksi sederhana dalam kelas.', 'Murid menunjukkan penguasaan yang baik dalam melafalkan kosa kata benda-benda di sekitar sekolah.'),
            ('KKA', 85, 'B', 'Murid menunjukkan penguasaan yang sangat baik dalam logika alur berpikir komputasional terurut dan pengenalan puzzle visual.', 'Murid perlu bimbingan dalam mengenali simbol antarmuka instruksi dasar koding anak.'),
            ('BAR', 90, 'A', 'Murid menunjukkan penguasaan yang sangat baik dalam menghafal mufrodat anggota tubuh dan ungkapan salam harian.', 'Murid menunjukkan penguasaan yang baik dalam menirukan pelafalan bunyi huruf hijaiyyah berharokat.'),
            ('BJW', 86, 'B', 'Murid menunjukkan penguasaan yang baik dalam menerapkan unggah-ungguh basa prasaja saat menyapa guru dan teman.', 'Murid menunjukkan penguasaan yang baik dalam mengenal nama-nama perabot rumah dalam basa ngoko.'),
        ]

        for kode, nilai, pred, cap_tinggi, cap_bimbingan in sample_nilai:
            pk = PembelajaranKelas.objects.get(kelas=kelas_1, mata_pelajaran=mupel_objects[kode], semester=sem1)
            NilaiAkhir.objects.update_or_create(
                anggota_kelas=anggota,
                pembelajaran_kelas=pk,
                defaults={
                    'nilai_angka': nilai,
                    'predikat': pred,
                    'capaian_tertinggi': cap_tinggi,
                    'capaian_perlu_bimbingan': cap_bimbingan
                }
            )
        self.stdout.write("- 11 Nilai Akhir Mata Pelajaran seeded")

        # 9. Kokurikuler
        KokurikulerNilai.objects.update_or_create(
            anggota_kelas=anggota,
            semester=sem1,
            aspek="Kokurikuler",
            defaults={
                'predikat': 'A',
                'deskripsi': 'Murid sangat baik dalam membiasakan sholat dhuha tepat waktu, sangat tertib dalam sholat berjamaah lima waktu di masjid sekolah, antusias mengikuti senam pagi ceria, konsisten membiasakan adab makan sehat halalan thoyyiban sambil duduk dan berdoa, serta aktif berolahraga dengan penuh sportivitas.'
            }
        )
        self.stdout.write("- Kokurikuler Nilai seeded")

        # 10. Ekstrakurikuler (6 Baris Lengkap)
        ekskul_data = [
            (1, 'Pramuka', 'A', 'Aktif dan terampil dalam kegiatan kepanduan siaga'),
            (2, 'Renang', 'B', 'Menguasai teknik dasar meluncur dan pernapasan air'),
            (3, 'Outbond', 'B', 'Berani dan kompak dalam kerjasama halang rintang'),
            (4, 'Lukis', 'A', 'Kreatif dalam gradasi warna dan komposisi gambar'),
            (5, '-', '-', '-'),
            (6, '-', '-', '-'),
        ]
        for urut, keg, pred, ket in ekskul_data:
            EkstrakurikulerNilai.objects.update_or_create(
                anggota_kelas=anggota,
                semester=sem1,
                urutan=urut,
                defaults={
                    'kegiatan': keg,
                    'predikat': pred,
                    'keterangan': ket
                }
            )
        self.stdout.write("- Ekstrakurikuler 6 Baris seeded")

        # 11. Prestasi (6 Baris Lengkap)
        prestasi_data = [
            (1, 'International Kangaroo Mathematics Contest', 'Juara 1 (Gold Medal) Level Benjamin'),
            (2, "Musabaqah Hifdzil Qur'an (MHQ) 1 Juz SDIT", 'Juara 2 Tingkat Kapanewon Ngaglik'),
            (3, 'Lomba Mewarnai Kaligrafi Islami DIY', 'Juara Harapan 1 Tingkat Kabupaten Sleman'),
            (4, '-', '-'),
            (5, '-', '-'),
            (6, '-', '-'),
        ]
        for urut, jenis, ket in prestasi_data:
            PrestasiMurid.objects.update_or_create(
                anggota_kelas=anggota,
                semester=sem1,
                urutan=urut,
                defaults={
                    'jenis_prestasi': jenis,
                    'keterangan': ket
                }
            )
        self.stdout.write("- Prestasi 6 Baris seeded")

        # 12. Ketidakhadiran (Halaman 6)
        Ketidakhadiran.objects.update_or_create(
            anggota_kelas=anggota,
            semester=sem1,
            defaults={
                'sakit': 4,
                'izin': 0,
                'tanpa_keterangan': 0
            }
        )
        self.stdout.write("- Ketidakhadiran (S:4, I:0, A:0) seeded")

        # 13. Catatan Wali Kelas (Halaman 4)
        CatatanWaliKelas.objects.update_or_create(
            anggota_kelas=anggota,
            semester=sem1,
            defaults={
                'catatan': 'Alhamdulillaah, ananda Arhan menunjukkan semangat belajar dan pembiasaan adab yang sangat membanggakan di semester ini, khususnya dalam ketekunan sholat dhuha berjamaah dan hafalan tahfidz juz 30. Tingkatkan konsentrasi dan ketelitian dalam latihan berhitung mandiri di rumah. Semoga Allah senantiasa menjaga ananda menjadi anak yang sholih, cerdas, dan senantiasa berbakti kepada orang tua. Barakallahu fiik.',
                'is_generated_by_ai': False
            }
        )
        self.stdout.write("- Catatan Wali Kelas seeded")

        self.stdout.write(self.style.SUCCESS("All initial and sample data successfully seeded into database!"))
