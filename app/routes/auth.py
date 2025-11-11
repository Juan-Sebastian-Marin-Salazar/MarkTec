from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.database import get_db_connection
import hashlib

bp = Blueprint("auth", __name__)

@bp.route("/")
def index():
    return redirect(url_for("auth.login"))

# ---------- LOGIN ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("user/login.html")

    correo = request.form.get("correo")
    password = request.form.get("password")
    clave_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT idUsuarios, nombre, matricula
        FROM usuarios
        WHERE correo=%s AND clave_hash=%s
    """, (correo, clave_hash))

    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if usuario:
        session["usuario_id"] = usuario["idUsuarios"]
        session["nombre"] = usuario["nombre"]
        session["matricula"] = usuario["matricula"]
        return redirect(url_for("auth.home"))

    flash("Correo o contraseña incorrectos")
    return redirect(url_for("auth.login"))

# ---------- REGISTRO ----------
@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        return render_template("user/registro.html")

    nombre = request.form.get("nombre")
    matricula = request.form.get("matricula")
    correo = request.form.get("correo")
    password = request.form.get("password")
    confirm = request.form.get("confirm")

    if password != confirm:
        flash("Las contraseñas no coinciden")
        return redirect(url_for("auth.registro"))

    clave_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios (nombre, correo, clave_hash, matricula)
            VALUES (%s, %s, %s, %s)
        """, (nombre, correo, clave_hash, matricula))
        conn.commit()
        flash("Registro exitoso. Inicia sesión.")
        return redirect(url_for("auth.login"))
    except:
        flash("El correo ya está registrado.")
        return redirect(url_for("auth.registro"))
    finally:
        cursor.close()
        conn.close()

# ---------- HOMEPAGE ----------
@bp.route("/pagina_principar")
def home():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template("user/pagina_principar.html",
                           nombre=session["nombre"],
                           matricula=session["matricula"])

# ---------- LOGOUT ----------
@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))