from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import jwt_required, get_jwt_claims
from blueprints import db, harus_pengguna
from blueprints.pengguna.model import Pengguna, Keluhan, KomentarKeluhan, DukungKeluhan
from password_strength import PasswordPolicy
from datetime import datetime
import hashlib


blueprint_pengguna = Blueprint("pengguna", __name__)
api = Api(blueprint_pengguna)


class PenggunaKeluhan(Resource):
    @jwt_required
    @harus_pengguna
    def get(self):
        daftar_keluhan = []
        klaim_pengguna = get_jwt_claims()
        parser = reqparse.RequestParser()
        parser.add_argument("halaman", type=int, location="args", default=1)
        parser.add_argument("per_halaman", type=int, location="args", default=10)
        args = parser.parse_args()

        # filter keluhan berdasarkan pengguna saat ini
        keluhan_pengguna = Keluhan.query.filter_by(id_pengguna=klaim_pengguna["id"])
        # limit keluhan sesuai jumlah per halaman
        total_keluhan = len(keluhan_pengguna.all())
        offset = (args["halaman"] - 1)*args["per_halaman"]
        keluhan_pengguna = keluhan_pengguna.limit(args["per_halaman"]).offset(offset)
        if total_keluhan%args["per_halaman"] != 0 or total_keluhan == 0:
            total_halaman = int(total_keluhan/args["per_halaman"]) + 1
        else:
            total_halaman = int(total_keluhan/args["per_halaman"])
        # menyatukan semua keluhan
        respons_keluhan = {
            "total_keluhan": total_keluhan, "halaman":args["halaman"],
            "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
        }
        for setiap_keluhan in keluhan_pengguna.all():
            daftar_keluhan.append(marshal(setiap_keluhan, Keluhan.respons))
        respons_keluhan["daftar_keluhan"] = daftar_keluhan
        return respons_keluhan, 200, {"Content-Type": "application/json"}

    @jwt_required
    @harus_pengguna
    def post(self):
        klaim_pengguna = get_jwt_claims()
        parser = reqparse.RequestParser()
        parser.add_argument("foto_sebelum", location="json", required=True)
        parser.add_argument("longitude", location="json", required=True)
        parser.add_argument("latitude", location="json", required=True)
        parser.add_argument("isi", location="json", required=True)
        parser.add_argument("anonim", location="json", type=bool, required=True)
        args = parser.parse_args()

        # menambahkan keluhan hanya jika pengguna sudah terverifikasi
        if klaim_pengguna["terverifikasi"]:
            keluhan = Keluhan(
                klaim_pengguna["id"], args["foto_sebelum"], klaim_pengguna["kota"],
                args["longitude"], args["latitude"], args["isi"], args["anonim"]
            )
            db.session.add(keluhan)
            db.session.commit()
            return marshal(keluhan, Keluhan.respons), 200, {"Content-Type": "application/json"}
        return {
            "status": "GAGAL",
            "pesan": "Anda harus terverifikasi untuk dapat membuat keluhan."
        }, 400, {"Content-Type": "application/json"}
        
    def options(self):
        return 200


class PenggunaKomentarKeluhan(Resource):
    # menambahkan komentar pada keluhan
    @jwt_required
    @harus_pengguna
    def post(self, id_keluhan=None):
        klaim_pengguna = get_jwt_claims()
        if id_keluhan is not None:
            parser = reqparse.RequestParser()
            parser.add_argument("isi", location="json", required=True)
            args = parser.parse_args()

            cari_keluhan = Keluhan.query.get(id_keluhan)
            if cari_keluhan is not None and klaim_pengguna["kota"] == cari_keluhan.kota:
                komentar_keluhan = KomentarKeluhan(klaim_pengguna["id"], id_keluhan, klaim_pengguna["kota"], args["isi"])
                db.session.add(komentar_keluhan)
                total_komentar = len(KomentarKeluhan.query.filter_by(id_keluhan=id_keluhan).all())
                cari_keluhan.total_komentar = total_komentar
                db.session.add(cari_keluhan)
                db.session.commit()
                # membentuk detail komentar
                data_pengguna = Pengguna.query.get(klaim_pengguna["id"])
                respons_komentar_keluhan = {
                    "avatar": data_pengguna.avatar,
                    "nama_depan": data_pengguna.nama_depan,
                    "nama_belakang": data_pengguna.nama_belakang,
                    "total_komentar": total_komentar,
                    "detail_komentar": marshal(komentar_keluhan, KomentarKeluhan.respons)
                }
                return respons_komentar_keluhan, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id_keluhan=None):
        return 200


class PenggunaDukungKeluhan(Resource):
    @jwt_required
    @harus_pengguna
    def get(self, id_keluhan=None):
        klaim_pengguna = get_jwt_claims()
        if id_keluhan is not None:
            cari_keluhan = Keluhan.query.get(id_keluhan)
            if cari_keluhan is not None and klaim_pengguna["kota"] == cari_keluhan.kota:
                # memeriksa apakah pengguna sudah mendukung keluhan atau belum
                filter_dukungan = DukungKeluhan.query.filter_by(
                    id_keluhan=id_keluhan, id_pengguna=klaim_pengguna["id"]
                )
                if filter_dukungan.all() == []:
                    return {
                        "status": "BERHASIL",
                        "pesan": "Anda belum mendukung keluhan ini.",
                        "dukung": False
                    }, 200, {"Content-Type": "application/json"}
                return {
                    "status": "BERHASIL",
                    "pesan": "Anda sudah mendukung keluhan ini.",
                    "dukung": True
                }, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    @jwt_required
    @harus_pengguna
    def put(self, id_keluhan=None):
        klaim_pengguna = get_jwt_claims()
        if id_keluhan is not None:
            cari_keluhan = Keluhan.query.get(id_keluhan)
            if cari_keluhan is not None and klaim_pengguna["kota"] == cari_keluhan.kota:
                # memeriksa apakah pengguna sudah mendukung keluhan atau belum
                filter_dukungan = DukungKeluhan.query.filter_by(
                    id_keluhan=id_keluhan, id_pengguna=klaim_pengguna["id"]
                )
                # jika belum mendukung, tambah dukungan dan perbarui tabel keluhan
                if filter_dukungan.all() == []:
                    dukung_keluhan = DukungKeluhan(klaim_pengguna["id"], id_keluhan)
                    db.session.add(dukung_keluhan)
                    total_dukungan = len(DukungKeluhan.query.filter_by(id_keluhan=id_keluhan).all())
                    cari_keluhan.total_dukungan = total_dukungan
                    db.session.add(cari_keluhan)
                    db.session.commit()
                    return {
                        "status": "BERHASIL",
                        "pesan": "Dukungan berhasil ditambahkan.",
                        "total_dukungan": total_dukungan,
                        "dukung": True
                    }, 200, {"Content-Type": "application/json"}
                # hapus dukungan jika sebelumnya belum mendukung
                db.session.delete(filter_dukungan.first())
                total_dukungan = len(DukungKeluhan.query.filter_by(id_keluhan=id_keluhan).all())
                cari_keluhan.total_dukungan = total_dukungan
                db.session.add(cari_keluhan)
                db.session.commit()
                return {
                    "status": "BERHASIL",
                    "pesan": "Dukungan berhasil dihapus.",
                    "total_dukungan": total_dukungan,
                    "dukung": False
                }, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id_keluhan=None):
        return 200


class PenggunaProfil(Resource):
    aturan_pwd = PasswordPolicy.from_names(
        length=8,
        uppercase=1,
        numbers=1,
        special=1
    )

    @jwt_required
    @harus_pengguna
    def get(self):
        klaim_pengguna = get_jwt_claims()
        cari_pengguna = Pengguna.query.get(klaim_pengguna["id"])
        return marshal(cari_pengguna, Pengguna.respons), 200, {"Content-Type": "application/json"}

    @jwt_required
    @harus_pengguna
    def put(self):
        parser = reqparse.RequestParser()
        argumen = [
            "avatar", "ktp",
            "nama_depan", "nama_belakang",
            "email_lama", "email_baru",
            "kata_sandi_lama", "kata_sandi_baru",
            "telepon_lama", "telepon_baru"
        ]
        for setiap_arg in argumen:
            parser.add_argument(setiap_arg, location="json")
        args = parser.parse_args()

        klaim_pengguna = get_jwt_claims()
        cari_pengguna = Pengguna.query.get(klaim_pengguna["id"])

        # pengecekan ketika pengguna mengganti kata sandi
        if args["kata_sandi_lama"] is not None:
            kata_sandi_lama = hashlib.md5(args["kata_sandi_lama"].encode()).hexdigest()
            if kata_sandi_lama != cari_pengguna.kata_sandi:
                return {
                    "status": "GAGAL",
                    "pesan": "Kata sandi yang anda masukan salah."
                }, 401, {"Content-Type": "application/json"}
            if args["kata_sandi_baru"] is not None:
                validasi = self.aturan_pwd.test(args["kata_sandi_baru"])
                if validasi != []:
                    return {
                        "status": "GAGAL",
                        "pesan": "Kata sandi tidak sesuai standar."
                    }, 400, {"Content-Type": "application/json"}
                kata_sandi_baru = hashlib.md5(args["kata_sandi_baru"].encode()).hexdigest()
                if kata_sandi_baru == cari_pengguna.kata_sandi:
                    return {
                        "status": "GAGAL",
                        "pesan": "Kata sandi baru harus berbeda dengan kata sandi lama."
                    }, 400, {"Content-Type": "application/json"}
                cari_pengguna.kata_sandi = hashlib.md5(args["kata_sandi_baru"].encode()).hexdigest()
                cari_pengguna.diperbarui = datetime.now()

        # pengecekan ketika pengguna mengganti email
        if args["email_lama"] is not None:
            if args["email_lama"] != cari_pengguna.email:
                return {
                    "status": "GAGAL",
                    "pesan": "Email yang anda masukan salah."
                }, 400, {"Content-Type": "application/json"}
            elif not args["email_baru"]:
                return {
                    "status": "GAGAL",
                    "pesan": "Email baru tidak boleh kosong."
                }, 400, {"Content-Type": "application/json"}
            elif args["email_baru"] == cari_pengguna.email:
                return {
                    "status": "GAGAL",
                    "pesan": "Email baru harus berbeda dengan email lama."
                }, 400, {"Content-Type": "application/json"}
            filter_kota = Pengguna.query.filter_by(kota=klaim_pengguna["kota"])
            filter_email = filter_kota.filter_by(email=args["email_baru"])
            if filter_email.all() != []:
                return {
                    "status": "GAGAL",
                    "pesan": "Email sudah ada yang memakai."
                }, 400, {"Content-Type": "application/json"}
            cari_pengguna.email = args["email_baru"]
            cari_pengguna.diperbarui = datetime.now()
        
        # pengecekan ketika pengguna mengganti nomor telepon
        if args["telepon_lama"] is not None:
            if args["telepon_lama"] != cari_pengguna.telepon:
                return {
                    "status": "GAGAL",
                    "pesan": "Nomor telepon yang anda masukan salah."
                }, 400, {"Content-Type": "application/json"}
            elif not args["telepon_baru"]:
                return {
                    "status": "GAGAL",
                    "pesan": "Nomor telepon baru tidak boleh kosong."
                }, 400, {"Content-Type": "application/json"}
            elif args["telepon_baru"] == cari_pengguna.telepon:
                return {
                    "status": "GAGAL",
                    "pesan": "Nomor telepon baru harus berbeda dengan nomor telepon lama."
                }, 400, {"Content-Type": "application/json"}
            filter_kota = Pengguna.query.filter_by(kota=klaim_pengguna["kota"])
            filter_telepon = filter_kota.filter_by(telepon=args["telepon_baru"])
            if filter_telepon.all() != []:
                return {
                    "status": "GAGAL",
                    "pesan": "Nomor telepon sudah ada yang memakai."
                }, 400, {"Content-Type": "application/json"}
            cari_pengguna.telepon = args["telepon_baru"]
            cari_pengguna.diperbarui = datetime.now()
        
        if args["ktp"] is not None:
            if cari_pengguna.terverifikasi:
                return {
                    "status": "GAGAL",
                    "pesan": "Anda tidak dapat mengubah ktp jika telah diverifikasi."
                }, 400, {"Content-Type": "application/json"}
            cari_pengguna.ktp = args["ktp"]
            cari_pengguna.diperbarui = datetime.now()
        if args["avatar"] is not None:
            cari_pengguna.avatar = args["avatar"]
            cari_pengguna.diperbarui = datetime.now()
        if args["nama_depan"]:
            cari_pengguna.nama_depan = args["nama_depan"]
            cari_pengguna.diperbarui = datetime.now()
        if args["nama_belakang"]:
            cari_pengguna.nama_belakang = args["nama_belakang"]
            cari_pengguna.diperbarui = datetime.now()
        
        db.session.add(cari_pengguna)
        db.session.commit()
        return marshal(cari_pengguna, Pengguna.respons), 200, {"Content-Type": "application/json"} 

    def options(self):
        return 200


api.add_resource(PenggunaKeluhan, "/keluhan")
api.add_resource(PenggunaKomentarKeluhan, "/keluhan/<int:id_keluhan>/komentar")
api.add_resource(PenggunaDukungKeluhan, "/keluhan/<int:id_keluhan>/dukungan")
api.add_resource(PenggunaProfil, "/profil")
