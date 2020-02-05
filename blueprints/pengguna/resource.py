from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import jwt_required, get_jwt_claims
from blueprints import db, harus_pengguna
from blueprints.pengguna.model import Pengguna, Keluhan
from password_strength import PasswordPolicy
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
        parser.add_argument("p", type=int, location="args", default=1)
        parser.add_argument("rp", type=int, location="args", default=10)
        args = parser.parse_args()

        # filter keluhan berdasarkan pengguna saat ini
        keluhan_pengguna = Keluhan.query.filter_by(id_pengguna=klaim_pengguna["id"])
        # limit keluhan sesuai jumlah per halaman
        total_keluhan = len(keluhan_pengguna.all())
        offset = (args["p"] - 1)*args["rp"]
        keluhan_pengguna = keluhan_pengguna.limit(args["rp"]).offset(offset)
        if total_keluhan%args["rp"] != 0 or total_keluhan == 0: total_halaman = int(total_keluhan/args["rp"]) + 1
        else: total_halaman = int(total_keluhan/args["rp"])
        # menyatukan semua keluhan
        respons_keluhan = {
            "total_keluhan": total_keluhan, "halaman":args["p"],
            "total_halaman":total_halaman, "per_halaman":args["rp"]
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


api.add_resource(PenggunaKeluhan, "/keluhan")
