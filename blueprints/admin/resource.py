from sqlalchemy import or_
from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_claims
from blueprints import db, harus_admin
from blueprints.pengguna.model import Pengguna, Keluhan, KomentarKeluhan
from blueprints.admin.model import Admin, Tanggapan
from password_strength import PasswordPolicy
from datetime import datetime
import hashlib


blueprint_admin = Blueprint("admin", __name__)
api = Api(blueprint_admin)


class AdminMasuk(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("email", location="json", required=True)
        parser.add_argument("kata_sandi", location="json", required=True)
        parser.add_argument("kota", location="json", required=True)
        args = parser.parse_args()
        
        kata_sandi = hashlib.md5(args["kata_sandi"].encode()).hexdigest()
        filter_kota = Admin.query.filter_by(kota=args["kota"])
        cari_admin = filter_kota.filter_by(aktif=True)
        cari_admin = cari_admin.filter_by(email=args["email"])
        cari_admin = cari_admin.filter_by(kata_sandi=kata_sandi).first()
        if cari_admin is None:
            return {
                "status": "GAGAL_MASUK",
                "pesan": "Email atau kata sandi salah."
            }, 401, {"Content-Type": "application/json"}
        
        klaim_admin = marshal(cari_admin, Admin.respons_jwt)
        klaim_admin["peran"] = "admin"
        klaim_admin["token"] = create_access_token(identity=cari_admin.id, user_claims=klaim_admin)
        return klaim_admin, 200, {"Content-Type": "application/json"}

    def options(self):
        return 200


class AdminKeluhan(Resource):
    # meninjaklanjuti keluhan pengguna oleh admin
    @jwt_required
    @harus_admin
    def put(self, id=None):
        parser = reqparse.RequestParser()
        parser.add_argument("isi", location="json", default="")
        parser.add_argument("foto_sesudah", location="json", default="")
        args = parser.parse_args()

        klaim_admin = get_jwt_claims()
        if id is not None:
            cari_keluhan = Keluhan.query.get(id)
            if cari_keluhan is not None and klaim_admin["kota"] == cari_keluhan.kota:
                if cari_keluhan.status != "selesai" and args["isi"]:
                    if cari_keluhan.status == "diterima": cari_keluhan.status = "diproses"
                    # foto sesudah hanya ditambahkan jika status berubah dari diproses menjadi selesai
                    elif cari_keluhan.status == "diproses":
                        cari_keluhan.status = "selesai"
                        cari_keluhan.foto_sesudah = args["foto_sesudah"]
                    tanggapan = Tanggapan(klaim_admin["id"], id, args["isi"])
                    db.session.add(tanggapan)
                    cari_keluhan.diperbarui = datetime.now()
                    db.session.commit()
                detail_keluhan = marshal(cari_keluhan, Keluhan.respons)
                id_pengguna = cari_keluhan.id_pengguna
                data_pengguna = Pengguna.query.get(id_pengguna)
                detail_keluhan["nama_depan"] = data_pengguna.nama_depan
                detail_keluhan["nama_belakang"] = data_pengguna.nama_belakang
                # mendapatkan semua tanggapan pada keluhan yang dipilih
                filter_tanggapan = Tanggapan.query.filter_by(id_keluhan=id)
                tanggapan_admin = []
                for setiap_tanggapan in filter_tanggapan.all():
                    tanggapan_admin.append(marshal(setiap_tanggapan, Tanggapan.respons))
                detail_keluhan["tanggapan_admin"] = tanggapan_admin
                return detail_keluhan, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id=None):
        return 200


class AdminPengguna(Resource):
    # menampilkan semua pengguna
    @jwt_required
    @harus_admin
    def get(self):
        klaim_admin = get_jwt_claims()
        parser = reqparse.RequestParser()
        parser.add_argument("kata_kunci", location="args")
        parser.add_argument(
            "status_aktif", location="args",
            choices=("aktif", "nonaktif", ""),
            help=("Masukan harus 'aktif' atau 'nonaktif'")
        )
        parser.add_argument(
            "status_terverifikasi", location="args",
            choices=("sudah", "belum", ""),
            help=("Masukan harus 'sudah' atau 'belum'")
        )
        parser.add_argument(
            "urutkan", location="args", default="dibuat",
            choices=("nama", "dibuat", "diperbarui", ""),
            help="Masukan harus 'nama', 'dibuat', atau 'diperbarui'"
        )
        parser.add_argument(
            "sortir", location="args", default="turun",
            choices=("naik", "turun", ""),
            help="Masukan harus 'naik' atau 'turun'"
        )
        parser.add_argument("halaman", type=int, location="args", default=1)
        parser.add_argument("per_halaman", type=int, location="args", default=10)
        args = parser.parse_args()
        
        # filter berdasarkan kota
        filter_pengguna = Pengguna.query.filter_by(kota=klaim_admin["kota"])
        # filter berdasarkan status aktif
        if args["status_aktif"]:
            status_aktif = True if args["status_aktif"] == "aktif" else False
            filter_pengguna = filter_pengguna.filter_by(aktif=status_aktif)
        # filter berdasarkan status terverifikasi
        if args["status_terverifikasi"]:
            status_terverifikasi = True if args["status_terverifikasi"] == "sudah" else False
            filter_pengguna = filter_pengguna.filter_by(terverifikasi=status_terverifikasi)
        # filter nama lengkap dan email berdasarkan kata kunci
        if args["kata_kunci"]:
            filter_pengguna = filter_pengguna.filter(or_(
                (Pengguna.nama_depan+" "+Pengguna.nama_belakang).like("%"+args["kata_kunci"]+"%"),
                Pengguna.email.like("%"+args["kata_kunci"]+"%")
            ))
        if args["urutkan"] is not None:
            # mengurutkan berdasarkan nama
            if args["urutkan"] == "nama":
                if args["sortir"] == "" or args["sortir"] == "turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.nama_depan.desc())
                elif args["sortir"] == "naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.nama_depan.asc())
            # mengurutkan berdasarkan dibuat
            elif args["urutkan"] == "dibuat" or args["urutkan"] == "":
                if args["sortir"] == "" or args["sortir"] == "turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.dibuat.desc())
                elif args["sortir"] == "naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.dibuat.asc())
            # mengurutkan berdasarkan diperbarui
            elif args["urutkan"] == "diperbarui":
                if args["sortir"] == "" or args["sortir"] == "turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.diperbarui.desc())
                elif args["sortir"] == "naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.diperbarui.asc())
        # limit pengguna sesuai jumlah per halaman
        total_pengguna = len(filter_pengguna.all())
        offset = (args["halaman"] - 1)*args["per_halaman"]
        filter_pengguna = filter_pengguna.limit(args["per_halaman"]).offset(offset)
        if total_pengguna%args["per_halaman"] != 0 or total_pengguna == 0:
            total_halaman = int(total_pengguna/args["per_halaman"]) + 1
        else:
            total_halaman = int(total_pengguna/args["per_halaman"])
        # menyatukan semua pengguna
        respons_pengguna = {
            "total_pengguna": total_pengguna, "halaman":args["halaman"],
            "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
        }
        daftar_pengguna = []
        for setiap_pengguna in filter_pengguna.all():
            daftar_pengguna.append(marshal(setiap_pengguna, Pengguna.respons))
        respons_pengguna["daftar_pengguna"] = daftar_pengguna
        return respons_pengguna, 200, {"Content-Type": "application/json"}

    # mengganti status aktif pengguna
    @jwt_required
    @harus_admin
    def put(self, id=None):
        klaim_admin = get_jwt_claims()
        if id is not None:
            cari_pengguna = Pengguna.query.get(id)
            if cari_pengguna.kota == klaim_admin["kota"]:
                cari_pengguna.aktif = False if cari_pengguna.aktif else True
                cari_pengguna.diperbarui = datetime.now()
                db.session.commit()
                return marshal(cari_pengguna, Pengguna.respons), 200, {
                    "Content-Type": "application/json"
                }
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Pengguna tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}
    
    # mengganti status terverifikasi pengguna
    @jwt_required
    @harus_admin
    def post(self, id=None):
        klaim_admin = get_jwt_claims()
        if id is not None:
            cari_pengguna = Pengguna.query.get(id)
            if cari_pengguna.kota == klaim_admin["kota"]:
                if not cari_pengguna.terverifikasi:
                    cari_pengguna.diperbarui = datetime.now()
                    cari_pengguna.terverifikasi = True
                    db.session.commit()
                return marshal(cari_pengguna, Pengguna.respons), 200, {
                    "Content-Type": "application/json"
                }
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Pengguna tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id=None):
        pass


class AdminKomentarKeluhan(Resource):
    # menampilkan semua komentar keluhan dari semua pengguna
    @jwt_required
    @harus_admin
    def get(self, id=None):
        klaim_admin = get_jwt_claims()
        parser = reqparse.RequestParser()
        parser.add_argument("id_komentar", location="args")
        parser.add_argument(
            "urutkan_laporan", location="args", default="laporan_turun",
            choices=("laporan_naik", "laporan_turun", ""),
            help="Masukan harus 'laporan_naik' atau 'laporan_turun'"
        )
        parser.add_argument(
            "urutkan", location="args", default="laporan",
            choices=("laporan", "dibuat", "diperbarui", ""),
            help="Masukan harus 'laporan', 'dibuat', atau 'diperbarui'"
        )
        parser.add_argument(
            "sortir", location="args", default="turun",
            choices=("naik", "turun", ""),
            help="Masukan harus 'naik' atau 'turun'"
        )
        parser.add_argument("halaman", type=int, location="args", default=1)
        parser.add_argument("per_halaman", type=int, location="args", default=10)
        args = parser.parse_args()
        
        # filter berdasarkan kota
        filter_komentar = KomentarKeluhan.query.filter_by(kota=klaim_admin["kota"])
        # filter berdasarkan id komentar
        if args["id_komentar"]:
            filter_komentar = filter_komentar.filter(KomentarKeluhan.id.like(args["id_komentar"]+"%"))
        if args["urutkan"] is not None:
            # mengurutkan berdasarkan laporan
            if args["urutkan"] == "laporan" or args["urutkan"] == "":
                if args["sortir"] == "" or args["sortir"] == "turun":
                    filter_komentar = filter_komentar.order_by(KomentarKeluhan.total_dilaporkan.desc())
                elif args["sortir"] == "naik":
                    filter_komentar = filter_komentar.order_by(KomentarKeluhan.total_dilaporkan.asc())
            # mengurutkan berdasarkan dibuat
            elif args["urutkan"] == "dibuat":
                if args["sortir"] == "" or args["sortir"] == "turun":
                    filter_komentar = filter_komentar.order_by(KomentarKeluhan.dibuat.desc())
                elif args["sortir"] == "naik":
                    filter_komentar = filter_komentar.order_by(KomentarKeluhan.dibuat.asc())
            # mengurutkan berdasarkan diperbarui
            elif args["urutkan"] == "diperbarui":
                if args["sortir"] == "" or args["sortir"] == "turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.diperbarui.desc())
                elif args["sortir"] == "naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.diperbarui.asc())
        # limit komentar sesuai jumlah per halaman
        total_komentar = len(filter_komentar.all())
        offset = (args["halaman"] - 1)*args["per_halaman"]
        filter_komentar = filter_komentar.limit(args["per_halaman"]).offset(offset)
        if total_komentar%args["per_halaman"] != 0 or total_komentar == 0:
            total_halaman = int(total_komentar/args["per_halaman"]) + 1
        else:
            total_halaman = int(total_komentar/args["per_halaman"])
        # menyatukan semua komentar
        respons_komentar = {
            "total_komentar": total_komentar, "halaman":args["halaman"],
            "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
        }
        daftar_komentar = []
        for setiap_komentar in filter_komentar.all():
            # mengambil nama pengguna dan email pada setiap komentar
            id_pengguna = setiap_komentar.id_pengguna
            data_pengguna = Pengguna.query.get(id_pengguna)
            # mengambil detail komentar
            data_komentar = {
                "avatar": data_pengguna.avatar,
                "email": data_pengguna.email,
                "nama_depan": data_pengguna.nama_depan,
                "nama_belakang": data_pengguna.nama_belakang,
                "detail_komentar": marshal(setiap_komentar, KomentarKeluhan.respons)
            }
            daftar_komentar.append(data_komentar)
        respons_komentar["daftar_komentar"] = daftar_komentar
        return respons_komentar, 200, {"Content-Type": "application/json"}

    # menghapus komentar keluhan dengan id tertentu
    @jwt_required
    @harus_admin
    def delete(self, id=None):
        klaim_admin = get_jwt_claims()
        if id is not None:
            cari_komentar = KomentarKeluhan.query.get(id)
            if cari_komentar is not None and cari_komentar.kota == klaim_admin["kota"]:
                db.session.delete(cari_komentar)
                db.session.commit()
                return {
                    "status": "BERHASIL",
                    "pesan": "Komentar dengan ID {id} berhasil dihapus.".format(id=id)
                }, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Komentar tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id=None):
        pass


api.add_resource(AdminMasuk, "/masuk")
api.add_resource(AdminKeluhan, "/keluhan/<int:id>")
api.add_resource(AdminPengguna, "/pengguna", "/pengguna/<int:id>")
api.add_resource(AdminKomentarKeluhan, "/keluhan/komentar", "/keluhan/komentar/<int:id>")
