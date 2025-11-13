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

# ---------- REGISTRO DE USUARIO ----------
@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        return render_template("user/registro.html")

    nombre = request.form.get("nombre")
    matricula = request.form.get("matricula")
    correo = request.form.get("correo")
    password = request.form.get("password")
    confirm = request.form.get("confirm")

    # Validaciones
    if not all([nombre, matricula, correo, password, confirm]):
        flash("Por favor completa todos los campos.")
        return render_template("user/registro.html")

    if password != confirm:
        flash("Las contraseñas no coinciden.")
        return render_template("user/registro.html")

    if not (correo.endswith("@mexicali.tecnm.mx") or correo.endswith("@itmexicali.edu.mx")):
        flash("Debes usar un correo institucional válido.")
        return render_template("user/registro.html")

    clave_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Crear usuario
        cursor.execute("""
            INSERT INTO usuarios (nombre, correo, clave_hash, matricula)
            VALUES (%s, %s, %s, %s)
        """, (nombre, correo, clave_hash, matricula))
        conn.commit()

        # Obtener ID del nuevo usuario
        cursor.execute("SELECT LAST_INSERT_ID()")
        nuevo_id = cursor.fetchone()[0]

        # Asignar rol por defecto 'comprador'
        cursor.execute("""
            INSERT INTO usuarios_roles (id_usuario, id_rol)
            SELECT %s, idRoles FROM roles WHERE nombre_rol = 'comprador'
        """, (nuevo_id,))
        conn.commit()

        flash("Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect(url_for("auth.login"))

    except Exception as e:
        conn.rollback()
        flash(f"Error al registrar usuario: {e}")
        return render_template("user/registro.html")

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
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT correo FROM usuarios WHERE idUsuarios=%s", (session["usuario_id"],))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    correo_usuario = usuario["correo"]

    # Etapa 1: Mostrar pantalla inicial
    if request.method == "GET":
        return render_template("user/verificacion.html", paso=1, correo=correo_usuario)

    # Etapa 2: Enviar código al correo
    if request.form.get("enviar_codigo"):
        codigo = str(random.randint(100000, 999999))
        session["codigo_verificacion"] = codigo
        enviar_codigo_email(correo_usuario, codigo)
        flash("Código enviado a tu correo.")
        return render_template("user/verificacion.html", paso=2, correo=correo_usuario)

    # Etapa 3: Validar código ingresado
    codigo_ingresado = request.form.get("codigo")
    codigo_real = session.get("codigo_verificacion")

    if codigo_ingresado == codigo_real:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Actualizar estado de verificación
        cursor.execute("""
            UPDATE usuarios
            SET es_vendedor_verificado = 1
            WHERE idUsuarios = %s
        """, (session["usuario_id"],))

        # Asignar rol 'vendedor' si aún no lo tiene
        cursor.execute("""
            INSERT INTO usuarios_roles (id_usuario, id_rol)
            SELECT %s, idRoles FROM roles
            WHERE nombre_rol = 'vendedor'
            AND idRoles NOT IN (
                SELECT id_rol FROM usuarios_roles WHERE id_usuario = %s
            )
        """, (session["usuario_id"], session["usuario_id"]))

        conn.commit()
        cursor.close()
        conn.close()

        # Limpiar sesión temporal
        session.pop("codigo_verificacion", None)

        flash("Tu cuenta ha sido verificada como vendedor.")
        return redirect(url_for("auth.home"))

    flash("El código es incorrecto.")
    return render_template("user/verificacion.html", paso=2, correo=correo_usuario)

# ---------- PÁGINA PRINCIPAL ----------
@bp.route("/pagina_principar")
def home():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener datos del usuario y todos sus roles
    cursor.execute("""
        SELECT 
            u.nombre, 
            u.matricula, 
            u.es_vendedor_verificado,
            GROUP_CONCAT(r.nombre_rol SEPARATOR ', ') AS roles
        FROM usuarios u
        LEFT JOIN usuarios_roles ur ON u.idUsuarios = ur.id_usuario
        LEFT JOIN roles r ON ur.id_rol = r.idRoles
        WHERE u.idUsuarios = %s
        GROUP BY u.idUsuarios
    """, (session["usuario_id"],))
    usuario = cursor.fetchone()

    cursor.close()
    conn.close()

    # Manejar caso sin roles
    roles_lista = []
    if usuario and usuario.get("roles"):
        roles_lista = [r.strip() for r in usuario["roles"].split(",")]

    # Pasar variable para que el HTML detecte si está verificado
    return render_template(
        "user/pagina_principar.html",
        nombre=usuario["nombre"],
        matricula=usuario["matricula"],
        roles=roles_lista,
        es_verificado=usuario["es_vendedor_verificado"] == 1
    )

# ---------- LOGOUT ----------
@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))