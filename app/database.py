import mysql.connector
from mysql.connector import Error
from app.config import Config

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT
        )
        return connection

    except Error as e:
        print("Error al conectar con MySQL:", e)
        return None