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
    kata_sandi = db.Column(db.String(100), nullable=False, default="")
    telepon = db.Column(db.String(15), nullable=False, default="")
    nomor_pln = db.Column(db.String(20), nullable=False, default="")
    nomor_bpjs = db.Column(db.String(20), nullable=False, default="")
    nomor_telkom = db.Column(db.String(20), nullable=False, default="")
    nomor_pdam = db.Column(db.String(20), nullable=False, default="")
    aktif = db.Column(db.Boolean, nullable=False, default=True)
    terverifikasi = db.Column(db.Boolean, nullable=False, default=False)
    dibuat = db.Column(db.DateTime, nullable=False)
    diperbarui = db.Column(db.DateTime, nullable=False)

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
        "telepon": fields.String,
        "nomor_pln": fields.String,
        "nomor_bpjs": fields.String,
        "nomor_telkom": fields.String,
        "nomor_pdam": fields.String,
        "aktif": fields.Boolean,
        "terverifikasi": fields.Boolean
    }

    respons_jwt = {
        "id": fields.Integer,
        "peran": fields.String,
        "kota": fields.String,
        "terverifikasi": fields.Boolean
    }

    def __init__(self, nama_depan, nama_belakang, kota, email, kata_sandi, telepon):
        self.nama_depan = nama_depan
        self.nama_belakang = nama_belakang
        self.kota = kota
        self.email = email
        self.kata_sandi = kata_sandi
        self.telepon = telepon
        self.dibuat = datetime.now()
        self.diperbarui = datetime.now()

    def __repr__(self):
        return "<Pengguna %r>" % self.id


class Keluhan(db.Model):
    __tablename__ = "keluhan"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_pengguna = db.Column(db.Integer, db.ForeignKey('pengguna.id'), nullable=False)
    foto_sebelum = db.Column(db.String(1000), nullable=False, default="")
    foto_sesudah = db.Column(db.String(1000), nullable=False, default="")
    kota = db.Column(db.String(20), nullable=False, default="")
    longitude = db.Column(db.String(100), nullable=False, default="")
    latitude = db.Column(db.String(100), nullable=False, default="")
    isi = db.Column(db.String(1000), nullable=False, default="")
    status = db.Column(db.String(10), nullable=False, default="diterima")
    dibaca = db.Column(db.Boolean, nullable=False, default=True)
    total_dukungan = db.Column(db.Integer, nullable=False, default=0)
    total_komentar = db.Column(db.Integer, nullable=False, default=0)
    anonim = db.Column(db.Boolean, nullable=False, default=False)
    dibuat = db.Column(db.DateTime, nullable=False)
    diperbarui = db.Column(db.DateTime, nullable=False)

    respons = {
        "dibuat": fields.DateTime,
        "diperbarui": fields.DateTime,
        "id": fields.Integer,
        "id_pengguna": fields.Integer,
        "foto_sebelum": fields.String,
        "foto_sesudah": fields.String,
        "kota": fields.String,
        "longitude": fields.String,
        "latitude": fields.String,
        "isi": fields.String,
        "status": fields.String,
        "dibaca": fields.Boolean,
        "anonim": fields.Boolean,
        "total_dukungan": fields.Integer,
        "total_komentar": fields.Integer
    }

    def __init__(self, id_pengguna, foto_sebelum, kota, longitude, latitude, isi, anonim):
        self.id_pengguna = id_pengguna
        self.foto_sebelum = foto_sebelum
        self.kota = kota
        self.longitude = longitude
        self.latitude = latitude
        self.isi = isi
        self.anonim = anonim
        self.dibuat = datetime.now()
        self.diperbarui = datetime.now()

    def __repr__(self):
        return "<Keluhan %r>" % self.id
