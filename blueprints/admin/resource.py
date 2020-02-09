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
                "status": "GAGAL_MASUK", "pesan": "Email atau kata sandi salah."
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
            daftar_pengguna = []
            parser = reqparse.RequestParser()
            parser.add_argument("halaman", type=int, location="args", default=1)
            parser.add_argument("per_halaman", type=int, location="args", default=10)
            args = parser.parse_args()
            
            # filter berdasarkan kota
            filter_keluhan = Keluhan.query.filter_by(kota=klaim_admin["kota"])
            # mengurutkan berdasarkan jumlah dukungan
            # mengurutkan berdasarkan tanggal diubah
            # filter berdasarkan status keluhan
            if args["status"] is not None:
                filter_keluhan = filter_keluhan.filter(Keluhan.status.like("%"+args["status"]+"%"))
            # limit keluhan sesuai jumlah per halaman
            total_keluhan = len(filter_keluhan.all())
            offset = (args["halaman"] - 1)*args["per_halaman"]
            filter_keluhan = filter_keluhan.limit(args["per_halaman"]).offset(offset)
            if total_keluhan%args["per_halaman"] != 0 or total_keluhan == 0:
                total_halaman = int(total_keluhan/args["per_halaman"]) + 1
            else:
                total_halaman = int(total_keluhan/args["per_halaman"])
            # menyatukan semua keluhan
            respons_keluhan = {
                "total_keluhan": total_keluhan, "halaman":args["halaman"],
                "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
            }
            for setiap_keluhan in filter_keluhan.all():
                data_keluhan = {}
                # mengambil nama pengguna pada setiap keluhan
                id_pengguna = setiap_keluhan.id_pengguna
                data_pengguna = Pengguna.query.get(id_pengguna)
                data_keluhan["nama_depan"] = data_pengguna.nama_depan
                data_keluhan["nama_belakang"] = data_pengguna.nama_belakang
                # mengambil detail keluhan
                data_keluhan["detail_keluhan"] = marshal(setiap_keluhan, Keluhan.respons)
                daftar_pengguna.append(data_keluhan)
            respons_keluhan["daftar_pengguna"] = daftar_pengguna
            return respons_keluhan, 200, {"Content-Type": "application/json"}

    # mengganti status aktif pengguna
    @jwt_required
    @harus_admin
    def put(self, id=None):
        pass
    
    # mengganti status terverifikasi pengguna
    @jwt_required
    @harus_admin
    def post(self, id=None):
        pass

    def options(self, id=None):
        pass


api.add_resource(AdminMasuk, "/masuk")
api.add_resource(AdminKeluhan, "/keluhan/<int:id>")
api.add_resource(AdminPengguna, "/pengguna", "/pengguna/<int:id>")
