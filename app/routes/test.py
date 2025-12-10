from flask import Blueprint, jsonify
from app.database import get_db_connection

bp = Blueprint("test", __name__)

@bp.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({"status": "OK", "mysql": result[0]})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500