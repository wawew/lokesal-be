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


api.add_resource(AdminMasuk, "/masuk")
api.add_resource(AdminKeluhan, "/keluhan/<int:id>")
