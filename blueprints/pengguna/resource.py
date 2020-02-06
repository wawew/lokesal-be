from flask import Blueprint
from flask_restful import Api, Resource, reqparse, marshal
from flask_jwt_extended import jwt_required, get_jwt_claims
from blueprints import db, harus_pengguna
from blueprints.pengguna.model import Pengguna, Keluhan, KomentarKeluhan, DukungKeluhan
from password_strength import PasswordPolicy
from datetime import datetime
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
        parser.add_argument("halaman", type=int, location="args", default=1)
        parser.add_argument("per_halaman", type=int, location="args", default=10)
        args = parser.parse_args()

        # filter keluhan berdasarkan pengguna saat ini
        keluhan_pengguna = Keluhan.query.filter_by(id_pengguna=klaim_pengguna["id"])
        # limit keluhan sesuai jumlah per halaman
        total_keluhan = len(keluhan_pengguna.all())
        offset = (args["halaman"] - 1)*args["per_halaman"]
        keluhan_pengguna = keluhan_pengguna.limit(args["per_halaman"]).offset(offset)
        if total_keluhan%args["per_halaman"] != 0 or total_keluhan == 0:
            total_halaman = int(total_keluhan/args["per_halaman"]) + 1
        else:
            total_halaman = int(total_keluhan/args["per_halaman"])
        # menyatukan semua keluhan
        respons_keluhan = {
            "total_keluhan": total_keluhan, "halaman":args["halaman"],
            "total_halaman":total_halaman, "per_halaman":args["per_halaman"]
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


class PenggunaKomentarKeluhan(Resource):
    # menambahkan komentar pada keluhan
    @jwt_required
    @harus_pengguna
    def post(self, id_keluhan=None):
        klaim_pengguna = get_jwt_claims()
        if id_keluhan is not None:
            parser = reqparse.RequestParser()
            parser.add_argument("isi", location="json", required=True)
            args = parser.parse_args()

            cari_keluhan = Keluhan.query.get(id_keluhan)
            if cari_keluhan is not None and klaim_pengguna["kota"] == cari_keluhan.kota:
                komentar_keluhan = KomentarKeluhan(klaim_pengguna["id"], id_keluhan, klaim_pengguna["kota"], args["isi"])
                db.session.add(komentar_keluhan)
                total_komentar = len(KomentarKeluhan.query.filter_by(id_keluhan=id_keluhan).all())
                cari_keluhan.total_komentar = total_komentar
                db.session.add(cari_keluhan)
                db.session.commit()
                respons_komentar_keluhan = marshal(komentar_keluhan, KomentarKeluhan.respons)
                respons_komentar_keluhan["total_komentar"] = total_komentar
                return respons_komentar_keluhan, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id_keluhan=None):
        return 200


class PenggunaDukungKeluhan(Resource):
    @jwt_required
    @harus_pengguna
    def put(self, id_keluhan=None):
        klaim_pengguna = get_jwt_claims()
        if id_keluhan is not None:
            cari_keluhan = Keluhan.query.get(id_keluhan)
            if cari_keluhan is not None and klaim_pengguna["kota"] == cari_keluhan.kota:
                # memeriksa apakah pengguna sudah mendukung keluhan atau belum
                filter_dukungan = DukungKeluhan.query.filter_by(
                    id_keluhan=id_keluhan, id_pengguna=klaim_pengguna["id"]
                )
                # jika belum mendukung, tambah dukungan dan perbarui tabel keluhan
                if filter_dukungan.all() == []:
                    dukung_keluhan = DukungKeluhan(klaim_pengguna["id"], id_keluhan)
                    db.session.add(dukung_keluhan)
                    total_dukungan = len(DukungKeluhan.query.filter_by(id_keluhan=id_keluhan).all())
                    cari_keluhan.total_dukungan = total_dukungan
                    db.session.add(cari_keluhan)
                    db.session.commit()
                    return {
                        "status": "BERHASIL",
                        "pesan": "Dukungan berhasil ditambahkan.",
                        "total_dukungan": total_dukungan,
                        "dukung": True
                    }, 200, {"Content-Type": "application/json"}
                # hapus dukungan jika sebelumnya belum mendukung
                db.session.delete(filter_dukungan.first())
                total_dukungan = len(DukungKeluhan.query.filter_by(id_keluhan=id_keluhan).all())
                cari_keluhan.total_dukungan = total_dukungan
                db.session.commit()
                return {
                    "status": "BERHASIL",
                    "pesan": "Dukungan berhasil dihapus.",
                    "total_keluhan": total_keluhan,
                    "dukung": False
                }, 200, {"Content-Type": "application/json"}
        return {
            "status": "TIDAK_KETEMU",
            "pesan": "Keluhan tidak ditemukan."
        }, 404, {"Content-Type": "application/json"}

    def options(self, id_keluhan=None):
        return 200


api.add_resource(PenggunaKeluhan, "/keluhan")
api.add_resource(PenggunaKomentarKeluhan, "/keluhan/<int:id_keluhan>/komentar")
api.add_resource(PenggunaDukungKeluhan, "/keluhan/<int:id_keluhan>/dukungan")
