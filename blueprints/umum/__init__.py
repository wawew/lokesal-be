from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token
from blueprints import db
from blueprints.pengguna.model import Pengguna
from password_strength import PasswordPolicy
import hashlib


blueprint_umum = Blueprint("umum", __name__)
api = Api(blueprint_umum)


class Daftar(Resource):
    aturan_pwd = PasswordPolicy.from_names(
        length=8,
        uppercase=1,
        numbers=1,
        special=1
    )
    
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("nama_depan", location="json", required=True)
        parser.add_argument("nama_belakang", location="json", required=True)
        parser.add_argument("kota", location="json", required=True)
        parser.add_argument("email", location="json", required=True)
        parser.add_argument("kata_sandi", location="json", required=True)
        args = parser.parse_args()
        
        validasi = self.aturan_pwd.test(args["kata_sandi"])
        if validasi == []:
            kata_sandi = hashlib.md5(args["kata_sandi"].encode()).hexdigest()
            pengguna = Pengguna(args["nama_depan"], args["nama_belakang"], args["kota"], args["email"], kata_sandi)
            filter_kota = Pengguna.query.filter_by(kota=args["kota"])
            filter_email = filter_kota.filter_by(email=args["email"])
            if filter_email.all() != []:
                return {"status": "GAGAL", "message": "Email sudah terdaftar."}, 400, {"Content-Type": "application/json"}
            db.session.add(pengguna)
            db.session.commit()
            return marshal(pengguna, Pengguna.respons), 200, {"Content-Type": "application/json"}
        return {"status": "GAGAL", "pesan": "Kata sandi tidak sesuai standar."}, 400, {"Content-Type": "application/json"}

    def options(self):
        return 200


api.add_resource(Daftar, "/daftar")
