from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.database import get_db_connection
import hashlib
import smtplib
from email.mime.text import MIMEText
import os
import random
from werkzeug.utils import secure_filename

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

# ---------- CREAR NUEVA PUBLICACIÓN (PRODUCTO) ----------
@bp.route("/nuevo-producto", methods=["GET", "POST"])
def nuevo_producto():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("user/nuevo_producto.html")

    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    precio = request.form.get("precio")
    imagenes = request.files.getlist("imagenes")

    if not titulo or not precio:
        flash("El título y el precio son obligatorios.")
        return redirect(url_for("auth.nuevo_producto"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1 Insertar la publicación
    cursor.execute("""
        INSERT INTO publicaciones (id_vendedor, titulo, descripcion, precio)
        VALUES (%s, %s, %s, %s)
    """, (session["usuario_id"], titulo, descripcion, precio))
    conn.commit()
    publicacion_id = cursor.lastrowid

    # 2 Procesar las imágenes (si existen)
    if imagenes:
        uploads_dir = os.path.join(os.path.dirname(__file__), "..", "static", "uploads")
        uploads_dir = os.path.abspath(uploads_dir)
        os.makedirs(uploads_dir, exist_ok=True)

        for i, img in enumerate(imagenes):
            if img and img.filename:
                filename = secure_filename(img.filename)
                ruta_absoluta = os.path.join(uploads_dir, filename)
                img.save(ruta_absoluta)
                # Construimos una URL accesible por el navegador: (esto se puede reemplazar luego por un URL remoto tipo S3)
                url_imagen = f"/static/uploads/{filename}"

                cursor.execute("""
                    INSERT INTO imagenes_publicacion (id_publicacion, url, texto_alternativo, orden)
                    VALUES (%s, %s, %s, %s)
                """, (publicacion_id, url_imagen, titulo, i))
        conn.commit()

    cursor.close()
    conn.close()

    flash("Tu publicación ha sido creada correctamente.")
    return redirect(url_for("auth.home"))

# ---------- ELIMINAR PUBLICACIÓN ----------
@bp.route("/eliminar-producto/<int:pub_id>", methods=["POST"])
def eliminar_producto(pub_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Validar que la publicación pertenece al usuario actual
    cursor.execute("""
        DELETE FROM publicaciones
        WHERE idPublicaciones = %s AND id_vendedor = %s
    """, (pub_id, session["usuario_id"]))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Publicación eliminada correctamente.")
    return redirect(url_for("auth.home"))

# ---------- PÁGINA PRINCIPAL ----------
@bp.route("/pagina_principar")
@bp.route("/home")  # alias para compatibilidad con url_for("auth.home")
def home():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Datos del usuario
    cursor.execute("""
        SELECT u.nombre, u.matricula, u.es_vendedor_verificado,
               GROUP_CONCAT(r.nombre_rol SEPARATOR ', ') AS roles
        FROM usuarios u
        LEFT JOIN usuarios_roles ur ON u.idUsuarios = ur.id_usuario
        LEFT JOIN roles r ON ur.id_rol = r.idRoles
        WHERE u.idUsuarios = %s
        GROUP BY u.idUsuarios
    """, (session["usuario_id"],))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.close()
        conn.close()
        return redirect(url_for("auth.logout"))

    # Cargar todas las publicaciones (para vista cliente)
    cursor.execute("""
        SELECT 
            p.idPublicaciones,
            p.id_vendedor,
            p.titulo,
            p.descripcion,
            p.precio,
            u.nombre AS vendedor,
            i.url AS imagen_url
        FROM publicaciones p
        JOIN usuarios u ON p.id_vendedor = u.idUsuarios
        LEFT JOIN imagenes_publicacion i 
            ON i.id_publicacion = p.idPublicaciones
            AND i.orden = (
                SELECT MIN(orden)
                FROM imagenes_publicacion
                WHERE id_publicacion = p.idPublicaciones
            )
        WHERE p.eliminado_en IS NULL
        ORDER BY p.creado_en DESC
    """)
    publicaciones_cliente = cursor.fetchall()

    # Cargar solo publicaciones del usuario (vista vendedor)
    cursor.execute("""
        SELECT 
            p.idPublicaciones,
            p.id_vendedor,
            p.titulo,
            p.descripcion,
            p.precio,
            u.nombre AS vendedor,
            i.url AS imagen_url
        FROM publicaciones p
        JOIN usuarios u ON p.id_vendedor = u.idUsuarios
        LEFT JOIN imagenes_publicacion i 
            ON i.id_publicacion = p.idPublicaciones
            AND i.orden = (
                SELECT MIN(orden)
                FROM imagenes_publicacion
                WHERE id_publicacion = p.idPublicaciones
            )
        WHERE p.eliminado_en IS NULL
          AND p.id_vendedor = %s
        ORDER BY p.creado_en DESC
    """, (session["usuario_id"],))
    publicaciones_vendedor = cursor.fetchall()

    cursor.close()
    conn.close()

    roles = usuario["roles"].split(", ") if usuario["roles"] else []
    es_verificado = bool(usuario["es_vendedor_verificado"])

    return render_template(
        "user/pagina_principar.html",
        nombre=usuario["nombre"],
        matricula=usuario["matricula"],
        roles=roles,
        es_verificado=es_verificado,
        publicaciones_cliente=publicaciones_cliente,
        publicaciones_vendedor=publicaciones_vendedor
    )

# ---------- LOGOUT ----------
@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))