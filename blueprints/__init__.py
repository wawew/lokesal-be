from flask_cors import CORS
from flask import Flask, request
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_claims
from datetime import timedelta
from functools import wraps
import json, random, string, os

app = Flask(__name__) # membuat semua blueprint
app.config["APP_DEBUG"] = True
CORS(app)

uname = os.environ["INI_UNAME"]
pwd = os.environ["INI_PWD"]
db_test = os.environ["INI_DB_TEST"]
db_dev = os.environ["INI_DB_DEV"]
db_endpoint = os.environ["INI_DB_ENDPOINT"]

try:
    env = os.environ.get("FLASK_ENV", "development")
    if env == "testing":
        app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://{uname}:{pwd}@{db_endpoint}:3306/{db_test}".format(uname=uname, pwd=pwd, db_test=db_test, db_endpoint=db_endpoint)
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://{uname}:{pwd}@{db_endpoint}:3306/{db_dev}".format(uname=uname, pwd=pwd, db_dev=db_dev, db_endpoint=db_endpoint)
except Exception as error:
    raise error

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "".join(random.choice(string.ascii_letters) for i in range(32))
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)


db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)
jwt = JWTManager(app)


def harus_pengembang(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        klaim_pengguna = get_jwt_claims()
        if klaim_pengguna["peran"] != "pengembang":
            return {"status": "DILARANG", "pesan": "Hanya pengembang yang diperkenankan untuk akses."}, 403
        return fn(*args, **kwargs)
    return wrapper

def harus_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        klaim_pengguna = get_jwt_claims()
        if klaim_pengguna["peran"] != "admin":
            return {"status": "DILARANG", "pesan": "Hanya admin yang diperkenankan untuk akses."}, 403
        return fn(*args, **kwargs)
    return wrapper

def harus_pengguna(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        klaim_pengguna = get_jwt_claims()
        if klaim_pengguna["peran"] != "pengguna":
            print(klaim_pengguna["peran"])
            return {"status": "DILARANG", "pesan": "Hanya pengguna yang diperkenankan untuk akses."}, 403
        return fn(*args, **kwargs)
    return wrapper


@app.after_request
def after_request(response):
    try:
        request_data = request.get_json()
    except:
        request_data = request.args.to_dict()
    if response.status_code == 200:
        app.logger.info("REQUEST_LOG\t%s", json.dumps({
            "method": request.method,
            "code": response.status,
            "request": request_data,
            "response": json.loads(response.data.decode("utf-8"))
        }))
    else:
        app.logger.error("REQUEST_LOG\t%s", json.dumps({
            "method": request.method,
            "code": response.status,
            "request": request_data,
            "response": json.loads(response.data.decode("utf-8"))
        }))
    return response


from blueprints.umum import blueprint_umum
from blueprints.pengguna.resource import blueprint_pengguna
from blueprints.pengembang import blueprint_pengembang

app.register_blueprint(blueprint_umum, url_prefix="")
app.register_blueprint(blueprint_pengguna, url_prefix="/pengguna")
app.register_blueprint(blueprint_pengembang, url_prefix="/pengembang")

db.create_all()
