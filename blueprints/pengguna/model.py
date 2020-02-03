from blueprints import db
from flask_restful import fields
from datetime import datetime


class Pengguna(db.Model):
    __tablename__ = "pengguna"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    avatar = db.Column(db.String(1000), nullable=False, default="")
    ktp = db.Column(db.String(1000), nullable=False, default="")
    nama_depan = db.Column(db.String(100), nullable=False, default="")
    nama_belakang = db.Column(db.String(100), nullable=False, default="")
    kota = db.Column(db.String(20), nullable=False, default="")
    email = db.Column(db.String(100), nullable=False, default="")
    password = db.Column(db.String(100), nullable=False, default="")
    telepon = db.Column(db.String(15), nullable=False, default="")
    nomor_pln = db.Column(db.String(15), nullable=False, default="")
    nomor_bpjs = db.Column(db.String(15), nullable=False, default="")
    nomor_telkom = db.Column(db.String(15), nullable=False, default="")
    nomor_pdam = db.Column(db.String(15), nullable=False, default="")
    aktif = db.Column(db.Boolean, nullable=False, default=True)
    terverifikasi = db.Column(db.Boolean, nullable=False, default=False)
    dibuat = db.Column(db.DateTime, default=datetime.now())
    diperbarui = db.Column(db.DateTime, default=datetime.now())

    respons = {
        "dibuat": fields.DateTime,
        "diperbarui": fields.DateTime,
        "id": fields.Integer,
        "avatar": fields.String,
        "ktp": fields.String,
        "nama_depan": fields.String,
        "nama_belakang": fields.String,
        "kota": fields.String,
        "email": fields.String,
        "password": fields.String,
        "telepon": fields.String,
        "nomor_pln": fields.String,
        "nomor_bpjs": fields.String,
        "nomor_telkom": fields.String,
        "nomor_pdam": fields.String,
        "aktif": fields.Boolean,
        "terverifikasi": fields.Boolean
    }

    respons_jwt_claim = {
        "id": fields.Integer,
        "peran": fields.String
    }

    def __init__(self, nama_depan, nama_belakang, email, password):
        self.nama_depan = nama_depan
        self.nama_belakang = nama_belakang
        self.email = email
        self.password = password

    def __repr__(self):
        return "<Pengguna %r>" % self.id
