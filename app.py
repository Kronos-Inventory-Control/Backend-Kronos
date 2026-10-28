from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

# 1. CONFIGURACIÓN DE LA BASE DE DATOS (MIGRADO A MYSQL)
USER_DB = 'root'        # Cambia por tu usuario de MySQL
PASS_DB = ''            # Cambia por tu contraseña de MySQL
URL_DB = 'localhost'
NAME_DB = 'panify'

# Usamos el driver mysql+pymysql para una conexión segura y limpia
FULL_URL_DB = f'mysql+pymysql://{USER_DB}:{PASS_DB}@{URL_DB}/{NAME_DB}'

app.config['SQLALCHEMY_DATABASE_URI'] = FULL_URL_DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialización de extensiones
db = SQLAlchemy(app)
migrate = Migrate(app, db)