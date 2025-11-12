from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.database import get_db_connection
import hashlib
import smtplib
from email.mime.text import MIMEText
import os
import random

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

# ---------- VERIFICACIÓN DE VENDEDOR POR CORREO ----------
def enviar_codigo_email(destinatario, codigo):
    remitente = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    mensaje = MIMEText(f"Tu código de verificación es: {codigo}")
    mensaje["Subject"] = "Código de verificación - Marketec"
    mensaje["From"] = f"Marketec <{remitente}>"
    mensaje["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, mensaje.as_string())


@bp.route("/verificar-vendedor", methods=["GET", "POST"])
def verificar_vendedor():
    # Validar sesión
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    # Obtener correo desde la BD
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT correo FROM usuarios WHERE idUsuarios=%s", (session["usuario_id"],))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    correo_usuario = usuario["correo"]

    # Protección contra POST inválidos
    if request.method == "POST" and \
       "codigo" not in request.form and \
       "enviar_codigo" not in request.form:
        return redirect(url_for("auth.verificar_vendedor"))

    # PRIMERA ETAPA (GET) - Mostrar pantalla inicial
    if request.method == "GET":
        return render_template("user/verificacion.html", paso=1, correo=correo_usuario)

    # SEGUNDA ETAPA - Enviar código al correo
    if request.form.get("enviar_codigo"):
        codigo = str(random.randint(100000, 999999))
        session["codigo_verificacion"] = codigo

        enviar_codigo_email(correo_usuario, codigo)
        flash("Código enviado a tu correo.")

        return render_template("user/verificacion.html", paso=2, correo=correo_usuario)

    # TERCERA ETAPA - Validar código ingresado
    codigo_ingresado = request.form.get("codigo")
    codigo_real = session.get("codigo_verificacion")

    if codigo_ingresado == codigo_real:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE usuarios
            SET es_vendedor_verificado=1
            WHERE idUsuarios=%s
        """, (session["usuario_id"],))
        conn.commit()
        cursor.close()
        conn.close()

        session.pop("codigo_verificacion", None)

        flash("Tu cuenta ha sido verificada como vendedor.")
        return redirect(url_for("auth.home"))

    # Código incorrecto
    flash("El código es incorrecto.")
    return render_template("user/verificacion.html", paso=2, correo=correo_usuario)

# ---------- HOMEPAGE ----------
@bp.route("/pagina_principar")
def home():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT nombre, matricula, es_vendedor_verificado
        FROM usuarios
        WHERE idUsuarios = %s
    """, (session["usuario_id"],))

    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template(
        "user/pagina_principar.html",
        nombre=usuario["nombre"],
        matricula=usuario["matricula"],
        es_verificado=usuario["es_vendedor_verificado"]
    )

# ---------- LOGOUT ----------
@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))