from sqlalchemy import func, or_
from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import create_access_token
from blueprints import db
from blueprints.pengguna.model import Pengguna, Keluhan, KomentarKeluhan, DukungKeluhan
from blueprints.admin.model import Tanggapan
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
                return {
                    "status": "GAGAL",
                    "pesan": "Email sudah ada yang memakai."
                }, 400, {"Content-Type": "application/json"}
            if filter_telepon.all() != []:
                return {
                    "status": "GAGAL",
                    "pesan": "Nomor telepon sudah ada yang memakai."
                }, 400, {"Content-Type": "application/json"}
            # jika email dan telepon unik pada kota yang ditentukan, pengguna didaftarkan
            pengguna = Pengguna(
                args["nama_depan"], args["nama_belakang"], args["kota"],
                args["email"], kata_sandi, args["telepon"]
            )
            db.session.add(pengguna)
            db.session.commit()
            # setelah didaftarkan, pengguna masuk
            klaim_pengguna = marshal(pengguna, Pengguna.respons_jwt)
            klaim_pengguna["peran"] = "pengguna"
            klaim_pengguna["token"] = create_access_token(identity=pengguna.id, user_claims=klaim_pengguna)
            return klaim_pengguna, 200, {"Content-Type": "application/json"}
        return {
            "status": "GAGAL",
            "pesan": "Kata sandi tidak sesuai standar."
        }, 400, {"Content-Type": "application/json"}

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
        cari_pengguna = filter_kota.filter_by(email=args["email"])
        cari_pengguna = cari_pengguna.filter_by(kata_sandi=kata_sandi).first()
        if cari_pengguna is None:
            return {
                "status": "GAGAL_MASUK",
                "pesan": "Email atau kata sandi salah."
            }, 401, {"Content-Type": "application/json"}
        elif cari_pengguna.aktif == False:
            return {
                "status": "GAGAL_MASUK",
                "pesan": "Akun anda telah dinonaktifkan. Silahkan hubungi Admin untuk informasi lebih lanjut."
            }, 401, {"Content-Type": "application/json"}
        klaim_pengguna = marshal(cari_pengguna, Pengguna.respons_jwt)
        klaim_pengguna["peran"] = "pengguna"
        klaim_pengguna["token"] = create_access_token(identity=cari_pengguna.id, user_claims=klaim_pengguna)
        return klaim_pengguna, 200, {"Content-Type": "application/json"}

    def options(self):
        return 200


class UmumKeluhan(Resource):
    # menampilkan semua keluhan pengguna
    def get(self, id=None):
        if id is None:
            parser = reqparse.RequestParser()
            parser.add_argument("kata_kunci", location="args")
            parser.add_argument("kota", location="args", required=True)
            parser.add_argument(
                "status", location="args",
                choices=("diterima", "diproses", "selesai", ""),
                help=("Masukan harus 'diterima', 'diproses' atau 'selesai'")
            )
            parser.add_argument(
                "kepuasan", location="args",
                choices=("puas", "tidak_puas", "belum", ""),
                help=("Masukan harus 'puas', 'tidak_puas' atau 'belum'")
            )
            parser.add_argument(
                "urutkan", location="args", default="dibuat",
                choices=("dukungan", "dibuat", "diperbarui", ""),
                help="Masukan harus 'dukungan', 'dibuat', atau 'diperbarui'"
            )
            parser.add_argument(
                "sortir", location="args", default="turun",
                choices=("naik", "turun", ""),
                help="Masukan harus 'naik' atau 'turun'"
            )
            parser.add_argument("halaman", type=int, location="args", default=1)
            parser.add_argument("per_halaman", type=int, location="args", default=10)
            args = parser.parse_args()
            
            filter_keluhan = db.session.query(
                Pengguna.nama_depan,
                Pengguna.nama_belakang,
                func.count(DukungKeluhan.id),
                Keluhan
            ).join(Pengguna, Pengguna.id==Keluhan.id_pengguna)\
            .outerjoin(DukungKeluhan, DukungKeluhan.id_keluhan==Keluhan.id).group_by(Keluhan.id)
            # filter berdasarkan kota
            filter_keluhan = filter_keluhan.filter(Keluhan.kota==args["kota"])
            # filter id berdasarkan id_keluhan
            if args["kata_kunci"]:
                filter_keluhan = filter_keluhan.filter(or_(
                    (Pengguna.nama_depan+" "+Pengguna.nama_belakang).like("%"+args["kata_kunci"]+"%"),
                    Keluhan.id.like(args["kata_kunci"]+"%")
                ))
            # filter berdasarkan status keluhan
            if args["status"]:
                filter_keluhan = filter_keluhan.filter(Keluhan.status.like("%"+args["status"]+"%"))
            # mengurutkan berdasarkan tingkat kepuasan
            if args["kepuasan"]:
                if args["kepuasan"] == "puas":
                    filter_keluhan = filter_keluhan.filter(Keluhan.kepuasan==True)
                elif args["kepuasan"] == "tidak_puas":
                    filter_keluhan = filter_keluhan.filter(Keluhan.kepuasan==False)
                elif args["kepuasan"] == "belum":
                    filter_keluhan = filter_keluhan.filter(Keluhan.kepuasan==None)
            if args["urutkan"] is not None:
                # mengurutkan berdasarkan jumlah dukungan
                if args["urutkan"] == "dukungan":
                    if args["sortir"] == "" or args["sortir"] == "turun":
                        filter_keluhan = filter_keluhan.order_by(Keluhan.total_dukungan.desc())
                    elif args["sortir"] == "naik":
                        filter_keluhan = filter_keluhan.order_by(Keluhan.total_dukungan.asc())
                # mengurutkan berdasarkan dibuat
                elif args["urutkan"] == "dibuat" or args["urutkan"] == "":
                    if args["sortir"] == "" or args["sortir"] == "turun":
                        filter_keluhan = filter_keluhan.order_by(Keluhan.dibuat.desc())
                    elif args["sortir"] == "naik":
                        filter_keluhan = filter_keluhan.order_by(Keluhan.dibuat.asc())
                # mengurutkan berdasarkan diperbarui
                elif args["urutkan"] == "diperbarui":
                    if args["sortir"] == "" or args["sortir"] == "turun":
                        filter_keluhan = filter_keluhan.order_by(Keluhan.diperbarui.desc())
                    elif args["sortir"] == "naik":
                        filter_keluhan = filter_keluhan.order_by(Keluhan.diperbarui.asc())
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
            daftar_keluhan = []
            for setiap_keluhan in filter_keluhan.all():
                data_keluhan = {
                    "nama_depan": setiap_keluhan[0],
                    "nama_belakang": setiap_keluhan[1],
                    "total_dukungan": setiap_keluhan[2],
                    "detail_keluhan": marshal(setiap_keluhan[3], Keluhan.respons)
                }
                daftar_keluhan.append(data_keluhan)
            respons_keluhan["daftar_keluhan"] = daftar_keluhan
            return respons_keluhan, 200, {"Content-Type": "application/json"}
        else:
            cari_keluhan = Keluhan.query.get(id)
            if cari_keluhan is None:
                return {
                    "status": "TIDAK_KETEMU",
                    "pesan": "Keluhan tidak ditemukan."
                }, 404, {"Content-Type": "application/json"}
            detail_keluhan = marshal(cari_keluhan, Keluhan.respons)
            # mendapatkan nama pengguna pada keluhan yang dipilih
            detail_keluhan["nama_depan"] = cari_keluhan.pengguna.nama_depan
            detail_keluhan["nama_belakang"] = cari_keluhan.pengguna.nama_belakang
            # mendapatkan semua tanggapan admin pada keluhan yang dipilih
            tanggapan_admin = []
            for setiap_tanggapan in cari_keluhan.tanggapan:
                tanggapan_admin.append(marshal(setiap_tanggapan, Tanggapan.respons))
            detail_keluhan["total_dukungan"] = len(cari_keluhan.dukung_keluhan)
            detail_keluhan["total_komentar"] = len(cari_keluhan.komentar_keluhan)
            detail_keluhan["tanggapan_admin"] = tanggapan_admin
            return detail_keluhan, 200, {"Content-Type": "application/json"}

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
            # menghitung jumlah per halaman
            total_komentar = len(filter_komentar.all())
            if total_komentar%args["per_halaman"] != 0 or total_komentar == 0:
                total_halaman = int(total_komentar/args["per_halaman"]) + 1
            else:
                total_halaman = int(total_komentar/args["per_halaman"])
            # menampilkan komentar dari halaman paling belakang
            offset = (total_halaman - args["halaman"])*args["per_halaman"]
            offset_baru = (total_komentar%args["per_halaman"]) + offset - args["per_halaman"]
            per_halaman = args["per_halaman"]
            # menampilkan komentar kosong jika halaman yang diminta lebih dari total halaman
            if args["halaman"] > total_komentar:
                filter_komentar = []
            else:
                if offset_baru < 0:
                    offset_baru = 0
                    per_halaman = total_komentar%args["per_halaman"]
                filter_komentar = filter_komentar.limit(per_halaman).offset(offset_baru).all()
            # menyatukan semua komentar
            respons_komentar = {
                "total_komentar":total_komentar, "halaman":args["halaman"],
                "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
            }
            for setiap_komentar in filter_komentar:
                data_komentar = {}
                # mengambil nama pengguna pada setiap komentar
                id_pengguna = setiap_komentar.id_pengguna
                data_pengguna = Pengguna.query.get(id_pengguna)
                data_komentar["avatar"] = data_pengguna.avatar
                data_komentar["nama_depan"] = data_pengguna.nama_depan
                data_komentar["nama_belakang"] = data_pengguna.nama_belakang
                # mengambil detail komentar
                data_komentar["detail_komentar"] = marshal(setiap_komentar, KomentarKeluhan.respons)
                daftar_komentar.append(data_komentar)
            respons_komentar["daftar_komentar"] = daftar_komentar
            return respons_komentar, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id=None):
        return 200


api.add_resource(UmumMasuk, "/masuk")
api.add_resource(UmumDaftar, "/daftar")
api.add_resource(UmumKeluhan, "/keluhan", "/keluhan/<int:id>")
api.add_resource(UmumTotalKeluhan, "/total_keluhan")
api.add_resource(UmumKomentarKeluhan, "/keluhan/<int:id>/komentar")
