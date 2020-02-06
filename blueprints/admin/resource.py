from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token, jwt_required
from blueprints import db, harus_admin
from blueprints.pengguna.model import Pengguna, Keluhan
from blueprints.admin.model import Admin
from password_strength import PasswordPolicy
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
        klaim_admin["token"] = create_access_token(identity=args["email"], user_claims=klaim_admin)
        return klaim_admin, 200, {"Content-Type": "application/json"}

    def options(self):
        return 200


class AdminKeluhan(Resource):
    @jwt_required
    @harus_admin
    def put(self, id=None):
        parser = reqparse.RequestParser()
        parser.add_argument("isi", location="json", required=True)
        parser.add_argument("foto_sesudah", location="json")
        args = parser.parse_args()

    def options(self, id=None):
        return 200


api.add_resource(AdminMasuk, "/masuk")
api.add_resource(AdminKeluhan, "/keluhan/<int:id>")
