from blueprints import db
from flask_restful import fields
from datetime import datetime


class Admin(db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kota = db.Column(db.String(20), nullable=False, default="")
    email = db.Column(db.String(100), nullable=False, default="")
    kata_sandi = db.Column(db.String(100), nullable=False, default="")
    aktif = db.Column(db.Boolean, nullable=False, default=True)
    tingkat = db.Column(db.Integer, nullable=False)
    dibuat = db.Column(db.DateTime, nullable=False)
    diperbarui = db.Column(db.DateTime, nullable=False)

    respons = {
        "dibuat": fields.DateTime(dt_format="iso8601"),
        "diperbarui": fields.DateTime(dt_format="iso8601"),
        "id": fields.Integer,
        "kota": fields.String,
        "email": fields.String,
        "aktif": fields.Boolean,
        "tingkat": fields.Integer
    }

    respons_jwt = {
        "id": fields.Integer,
        "kota": fields.String,
        "tingkat": fields.Integer
    }

    def __init__(self, kota, email, kata_sandi, tingkat):
        self.kota = kota
        self.email = email
        self.kata_sandi = kata_sandi
        self.tingkat = tingkat
        self.dibuat = datetime.now()
        self.diperbarui = datetime.now()

    def __repr__(self):
        return "<Admin %r>" % self.id