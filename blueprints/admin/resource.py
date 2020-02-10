from sqlalchemy import or_
from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_claims
from blueprints import db, harus_admin
from blueprints.pengguna.model import Pengguna, Keluhan
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
                    # foto sesudah hanya ditambahkan jika status--
                    # --berubah dari diproses menjadi selesai
                    elif cari_keluhan.status == "diproses":
                        cari_keluhan.status = "selesai"
                        cari_keluhan.foto_sesudah = args["foto_sesudah"]
                    tanggapan = Tanggapan(klaim_admin["id"], id, args["isi"])
                    db.session.add(tanggapan)
                    cari_keluhan.diperbarui = datetime.now()
                    db.session.add(cari_keluhan)
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
    def get(self, id=None):
        klaim_admin = get_jwt_claims()
        if id is None:
            parser = reqparse.RequestParser()
            parser.add_argument("kata_kunci", location="args")
            parser.add_argument(
                "status_aktif", location="args",
                choices=("aktif", "nonaktif"),
                help=("Masukan harus 'aktif' atau 'nonaktif'")
            )
            parser.add_argument(
                "status_terverifikasi", location="args",
                choices=("sudah", "belum"),
                help=("Masukan harus 'sudah' atau 'belum'")
            )
            parser.add_argument(
                "urutkan_nama", location="args",
                choices=("nama_naik", "nama_turun"),
                help="Masukan harus 'nama_naik' atau 'nama_turun'"
            )
            parser.add_argument(
                "urutkan_diperbarui", location="args", default="diperbarui_turun",
                choices=("diperbarui_naik", "diperbarui_turun"),
                help="Masukan harus 'diperbarui_naik' atau 'diperbarui_turun'"
            )
            parser.add_argument(
                "urutkan_dibuat", location="args",
                choices=("dibuat_naik", "dibuat_turun"),
                help="Masukan harus 'dibuat_naik' atau 'dibuat_turun'"
            )
            parser.add_argument("halaman", type=int, location="args", default=1)
            parser.add_argument("per_halaman", type=int, location="args", default=10)
            args = parser.parse_args()
            
            # filter berdasarkan kota
            filter_pengguna = Pengguna.query.filter_by(kota=klaim_admin["kota"])
            # filter berdasarkan status aktif
            if args["status_aktif"] is not None:
                status_aktif = True if args["status_aktif"] == "aktif" else False
                filter_pengguna = filter_pengguna.filter_by(aktif=status_aktif)
            # filter berdasarkan status terverifikasi
            if args["status_terverifikasi"] is not None:
                status_terverifikasi = True if args["status_terverifikasi"] == "sudah" else False
                filter_pengguna = filter_pengguna.filter_by(terverifikasi=status_terverifikasi)
            # filter nama lengkap dan email berdasarkan kata kunci
            if args["kata_kunci"] is not None:
                filter_pengguna = filter_pengguna.filter(or_(
                    (Pengguna.nama_depan+" "+Pengguna.nama_belakang).like("%"+args["kata_kunci"]+"%"),
                    Pengguna.email.like("%"+args["kata_kunci"]+"%")
                ))
            # mengurutkan berdasarkan nama
            if args["urutkan_nama"] is not None:
                if args["urutkan_nama"] == "nama_naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.nama_depan.asc())
                elif args["urutkan_nama"] == "nama_turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.nama_depan.desc())
            # mengurutkan berdasarkan diperbarui
            if args["urutkan_diperbarui"] is not None:
                if args["urutkan_diperbarui"] == "diperbarui_naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.diperbarui.asc())
                elif args["urutkan_diperbarui"] == "diperbarui_turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.diperbarui.desc())
            # mengurutkan berdasarkan dibuat
            if args["urutkan_dibuat"] is not None:
                if args["urutkan_dibuat"] == "dibuat_naik":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.dibuat.asc())
                elif args["urutkan_dibuat"] == "dibuat_turun":
                    filter_pengguna = filter_pengguna.order_by(Pengguna.dibuat.desc())
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
        else:
            cari_pengguna = Pengguna.query.get(id)
            if cari_pengguna.kota != klaim_admin["kota"]:
                return {
                    "status": "TIDAK_KETEMU",
                    "pesan": "Pengguna tidak ditemukan."
                }, 404, {"Content-Type": "application/json"}
            return marshal(cari_pengguna, Pengguna.respons), 200, {"Content-Type": "application/json"}

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
                db.session.add(cari_pengguna)
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
                    db.session.add(cari_pengguna)
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


api.add_resource(AdminMasuk, "/masuk")
api.add_resource(AdminKeluhan, "/keluhan/<int:id>")
api.add_resource(AdminPengguna, "/pengguna", "/pengguna/<int:id>")
