from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token, jwt_required
from blueprints import db, harus_pengembang
from blueprints.admin.model import Admin
from password_strength import PasswordPolicy
import hashlib, os


email_pengembang = os.environ["INI_EMAIL_LOKESAL"]
kata_sandi_pengembang = os.environ["INI_PWD_LOKESAL"]


blueprint_pengembang = Blueprint("pengembang", __name__)
api = Api(blueprint_pengembang)


class PengembangMasuk(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("email", location="json", required=True)
        parser.add_argument("kata_sandi", location="json", required=True)
        args = parser.parse_args()
        
        if args["email"] != email_pengembang or args["kata_sandi"] != kata_sandi_pengembang:
            return {
                "status": "GAGAL_MASUK", "pesan": "Email atau kata sandi salah."
            }, 401, {"Content-Type": "application/json"}
        
        klaim_pengembang = {"peran": "pengembang"}
        klaim_pengembang["token"] = create_access_token(identity=args["email"], user_claims=klaim_pengembang)
        return klaim_pengembang, 200, {"Content-Type": "application/json"}

    def options(self):
        return 200


class ManajemenAdmin(Resource):
    aturan_pwd = PasswordPolicy.from_names(
        length=8,
        uppercase=1,
        numbers=1,
        special=1
    )
    
    # Mendaftarkan admin baru pada kota tertentu
    @jwt_required
    @harus_pengembang
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("kota", location="json", required=True)
        parser.add_argument("email", location="json", required=True)
        parser.add_argument("kata_sandi", location="json", required=True)
        parser.add_argument("tingkat", location="json", type=int, required=True)
        args = parser.parse_args()
        
        validasi = self.aturan_pwd.test(args["kata_sandi"])
        if validasi == []:
            # mencari apakah email sudah terdaftar di kota yang sama
            kata_sandi = hashlib.md5(args["kata_sandi"].encode()).hexdigest()
            filter_kota = Admin.query.filter_by(kota=args["kota"])
            filter_email = filter_kota.filter_by(email=args["email"])
            if filter_email.all() != []:
                return {"status": "GAGAL", "pesan": "Email sudah terdaftar."}, 400, {"Content-Type": "application/json"}
            # jika email unik pada kota yang ditentukan, admin didaftarkan
            admin = Admin(args["kota"], args["email"], kata_sandi, args["tingkat"])
            db.session.add(admin)
            db.session.commit()
            return marshal(admin, Admin.respons), 200, {"Content-Type": "application/json"}
        return {"status": "GAGAL", "pesan": "Kata sandi tidak sesuai standar."}, 400, {"Content-Type": "application/json"}

    def options(self, id=None):
        return 200


api.add_resource(ManajemenAdmin, "/admin", "/admin/<int:id>")
api.add_resource(PengembangMasuk, "/masuk")
