from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token
from blueprints import db
from blueprints.pengguna.model import Pengguna, Keluhan, KomentarKeluhan
from password_strength import PasswordPolicy
import hashlib


blueprint_umum = Blueprint("umum", __name__)
api = Api(blueprint_umum)


class UmumDaftar(Resource):
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
        parser.add_argument("telepon", location="json", required=True)
        args = parser.parse_args()
        
        validasi = self.aturan_pwd.test(args["kata_sandi"])
        if validasi == []:
            # mencari apakah email sudah terdaftar di kota tertentu
            kata_sandi = hashlib.md5(args["kata_sandi"].encode()).hexdigest()
            filter_kota = Pengguna.query.filter_by(kota=args["kota"])
            filter_email = filter_kota.filter_by(email=args["email"])
            filter_telepon = filter_kota.filter_by(telepon=args["telepon"])
            if filter_email.all() != []:
                return {"status": "GAGAL", "pesan": "Email sudah terdaftar."}, 400, {"Content-Type": "application/json"}
            if filter_telepon.all() != []:
                return {"status": "GAGAL", "pesan": "Telepon sudah terdaftar."}, 400, {"Content-Type": "application/json"}
            # jika email dan telepon unik pada kota yang ditentukan, pengguna didaftarkan
            pengguna = Pengguna(args["nama_depan"], args["nama_belakang"], args["kota"], args["email"], kata_sandi, args["telepon"])
            db.session.add(pengguna)
            db.session.commit()
            # setelah didaftarkan, pengguna masuk
            klaim_pengguna = marshal(pengguna, Pengguna.respons_jwt)
            klaim_pengguna["peran"] = "pengguna"
            klaim_pengguna["token"] = create_access_token(identity=args["email"], user_claims=klaim_pengguna)
            return klaim_pengguna, 200, {"Content-Type": "application/json"}
        return {"status": "GAGAL", "pesan": "Kata sandi tidak sesuai standar."}, 400, {"Content-Type": "application/json"}

    def options(self):
        return 200


class UmumMasuk(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("email", location="json", required=True)
        parser.add_argument("kata_sandi", location="json", required=True)
        parser.add_argument("kota", location="json", required=True)
        args = parser.parse_args()
        
        kata_sandi = hashlib.md5(args["kata_sandi"].encode()).hexdigest()
        filter_kota = Pengguna.query.filter_by(kota=args["kota"])
        cari_pengguna = filter_kota.filter_by(aktif=True)
        cari_pengguna = cari_pengguna.filter_by(email=args["email"])
        cari_pengguna = cari_pengguna.filter_by(kata_sandi=kata_sandi).first()
        if cari_pengguna is None:
            return {
                "status": "GAGAL_MASUK", "pesan": "Email atau kata sandi salah."
            }, 401, {"Content-Type": "application/json"}
        
        klaim_pengguna = marshal(cari_pengguna, Pengguna.respons_jwt)
        klaim_pengguna["peran"] = "pengguna"
        klaim_pengguna["token"] = create_access_token(identity=args["email"], user_claims=klaim_pengguna)
        return klaim_pengguna, 200, {"Content-Type": "application/json"}

    def options(self):
        return 200


class UmumKeluhan(Resource):
    def get(self, id=None):
        if id is None:
            daftar_keluhan = []
            parser = reqparse.RequestParser()
            parser.add_argument("status", location="args")
            parser.add_argument("kota", location="args", required=True)
            parser.add_argument("halaman", type=int, location="args", default=1)
            parser.add_argument("per_halaman", type=int, location="args", default=10)
            args = parser.parse_args()
            
            # filter berdasarkan kota
            filter_keluhan = Keluhan.query.filter_by(kota=args["kota"])
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
                daftar_keluhan.append(data_keluhan)
            respons_keluhan["daftar_keluhan"] = daftar_keluhan
            return respons_keluhan, 200, {"Content-Type": "application/json"}
        else:
            filter_keluhan = Keluhan.query.get(id)
            if filter_keluhan is None:
                return {
                    "status": "TIDAK_KETEMU",
                    "pesan": "Keluhan tidak ditemukan."
                }, 404, {"Content-Type": "application/json"}
            return marshal(filter_keluhan, Keluhan.respons), 200, {"Content-Type": "application/json"}

    def options(self, id=None):
        return 200


class UmumTotalKeluhan(Resource):
    def get(self):
        total_keluhan = {}
        parser = reqparse.RequestParser()
        parser.add_argument("kota", location="args", required=True)
        args = parser.parse_args()

        filter_keluhan = Keluhan.query.filter_by(kota=args["kota"])
        total_keluhan["diterima"] = len(filter_keluhan.filter_by(status="diterima").all())
        total_keluhan["diproses"] = len(filter_keluhan.filter_by(status="diproses").all())
        total_keluhan["selesai"] = len(filter_keluhan.filter_by(status="selesai").all())
        return total_keluhan, 200, {"Content-Type": "application/json"}

    def options(self):
        return 200


class UmumKomentarKeluhan(Resource):
    # menampilkan semua komentar pada keluhan yang dipilih
    def get(self, id=None):
        if id is not None:
            daftar_komentar = []
            parser = reqparse.RequestParser()
            parser.add_argument("halaman", type=int, location="args", default=1)
            parser.add_argument("per_halaman", type=int, location="args", default=10)
            args = parser.parse_args()

            # filter berdasarkan id keluhan
            filter_komentar = KomentarKeluhan.query.filter_by(id_keluhan=id)
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
                "total_komentar":total_komentar, "halaman":args["halaman"],
                "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
            }
            for setiap_komentar in filter_komentar.all():
                data_komentar = {}
                # mengambil nama pengguna pada setiap keluhan
                id_pengguna = setiap_komentar.id_pengguna
                data_pengguna = Pengguna.query.get(id_pengguna)
                data_komentar["avatar"] = data_pengguna.avatar
                data_komentar["nama_depan"] = data_pengguna.nama_depan
                data_komentar["nama_belakang"] = data_pengguna.nama_belakang
                # mengambil detail keluhan
                data_komentar["detil_komentar"] = marshal(setiap_komentar, KomentarKeluhan.respons)
                daftar_komentar.append(data_komentar)
            respons_komentar["daftar_komentar"] = daftar_komentar
            return respons_komentar, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}


api.add_resource(UmumMasuk, "/masuk")
api.add_resource(UmumDaftar, "/daftar")
api.add_resource(UmumKeluhan, "/keluhan", "/keluhan/<int:id>")
api.add_resource(UmumTotalKeluhan, "/total_keluhan")
api.add_resource(UmumKomentarKeluhan, "/keluhan/<int:id>/komentar")
