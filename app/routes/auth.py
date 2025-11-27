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
        SELECT idUsuarios, nombre, matricula, telefono
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
        # almacenar telefono en sesión puede ser útil (opcional)
        session["telefono"] = usuario.get("telefono")
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
    telefono = request.form.get("telefono")            # <-- CORRECCIÓN: usar .get()
    correo = request.form.get("correo")
    password = request.form.get("password")
    confirm = request.form.get("confirm")

    # Validaciones
    if not all([nombre, matricula, correo, password, confirm, telefono]):
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
        # Crear usuario (agregado telefono)
        cursor.execute("""
            INSERT INTO usuarios (nombre, correo, clave_hash, matricula, telefono)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, correo, clave_hash, matricula, telefono))
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

    # ==== GET: Cargar categorías desde SQL ====
    if request.method == "GET":
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT idCategorias, nombre_categoria
            FROM categorias
            WHERE esta_activa = 1
            ORDER BY nombre_categoria
        """)
        categorias = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("user/nuevo_producto.html", categorias=categorias)

    # ==== POST: Crear publicación ====
    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    precio = request.form.get("precio")
    categoria_id = request.form.get("categoria")
    imagenes = request.files.getlist("imagenes")

    if not titulo or not precio or not categoria_id:
        flash("Título, precio y categoría son obligatorios.")
        return redirect(url_for("auth.nuevo_producto"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Insertar la publicación
    cursor.execute("""
        INSERT INTO publicaciones (id_vendedor, titulo, descripcion, precio)
        VALUES (%s, %s, %s, %s)
    """, (session["usuario_id"], titulo, descripcion, precio))
    conn.commit()
    publicacion_id = cursor.lastrowid

    # 2. Guardar categoría en tabla puente
    cursor.execute("""
        INSERT INTO publicaciones_categoria (id_publicacion, id_categoria)
        VALUES (%s, %s)
    """, (publicacion_id, categoria_id))
    conn.commit()

    # 3. Guardar imágenes localmente
    if imagenes:
        uploads_dir = os.path.join(os.getcwd(), "app", "static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        for i, img in enumerate(imagenes):
            if img and img.filename:
                filename = secure_filename(img.filename)
                ruta_absoluta = os.path.join(uploads_dir, filename)
                img.save(ruta_absoluta)

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

# ---------- DETALLE PUBLICACIÓN (PRODUCTO) ----------
@bp.route("/producto/<int:pub_id>")
def detalle_producto(pub_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener datos del producto (incluye telefono del vendedor)
    cursor.execute("""
        SELECT p.*, u.nombre AS vendedor, u.telefono AS telefono_vendedor
        FROM publicaciones p
        JOIN usuarios u ON p.id_vendedor = u.idUsuarios
        WHERE p.idPublicaciones = %s
    """, (pub_id,))
    producto = cursor.fetchone()

    if not producto:
        cursor.close()
        conn.close()
        return "Producto no encontrado", 404

    # Obtener imágenes (ordenadas)
    cursor.execute("""
        SELECT url 
        FROM imagenes_publicacion
        WHERE id_publicacion = %s
        ORDER BY orden ASC
    """, (pub_id,))
    imagenes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "user/producto.html",
        producto=producto,
        imagenes=imagenes
    )

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

# ---------- INICIAR TRANSACCION ----------
@bp.route("/crear-transaccion/<int:pub_id>", methods=["POST"])
def crear_transaccion(pub_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    comprador_id = session["usuario_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener vendedor de la publicación
    cursor.execute("SELECT id_vendedor FROM publicaciones WHERE idPublicaciones=%s", (pub_id,))
    pub = cursor.fetchone()

    if not pub:
        flash("Publicación no encontrada.")
        return redirect(url_for("auth.home"))

    vendedor_id = pub["id_vendedor"]

    # Insertar transacción
    cursor.execute("""
        INSERT INTO transaccion (id_vendedor, id_comprador, id_publicacion)
        VALUES (%s, %s, %s)
    """, (vendedor_id, comprador_id, pub_id))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Transacción creada. Esperando confirmación del vendedor.")
    return redirect(url_for("auth.home"))

# ---------- CONFIRMAR TRANSACCION ----------
@bp.route("/confirmar-transaccion/<int:trans_id>", methods=["POST"])
def confirmar_transaccion(trans_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    vendedor_id = session["usuario_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE transaccion
        SET estado = 'finalizada'
        WHERE id_transaccion = %s AND id_vendedor = %s
    """, (trans_id, vendedor_id))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Transacción confirmada. El comprador será notificado.")
    return redirect(url_for("auth.home"))

# ----------- CANCELAR TRANSACCION ----------
@bp.route("/cancelar-transaccion/<int:trans_id>", methods=["POST"])
def cancelar_transaccion(trans_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    vendedor_id = session["usuario_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Validar que la transacción pertenece al vendedor actual
    cursor.execute("""
        SELECT id_comprador FROM transaccion
        WHERE id_transaccion = %s AND id_vendedor = %s
    """, (trans_id, vendedor_id))
    transaccion = cursor.fetchone()

    if not transaccion:
        flash("Transacción no encontrada o no pertenece a tu cuenta.")
        cursor.close()
        conn.close()
        return redirect(url_for("auth.home"))

    # Actualizar estado a cancelada
    cursor.execute("""
        UPDATE transaccion
        SET estado = 'cancelada'
        WHERE id_transaccion = %s AND id_vendedor = %s
    """, (trans_id, vendedor_id))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Transacción cancelada correctamente. El comprador ha sido notificado.")
    return redirect(url_for("auth.home"))

# ---------- MIS TRANSACCIONES ----------
@bp.route("/mis-transacciones")
def mis_transacciones():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    vendedor_id = session["usuario_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            t.id_transaccion,
            t.estado,
            t.fecha_creacion,
            u.nombre AS comprador,
            p.titulo AS producto
        FROM transaccion t
        JOIN usuarios u ON t.id_comprador = u.idUsuarios
        JOIN publicaciones p ON t.id_publicacion = p.idPublicaciones
        WHERE t.id_vendedor = %s
        ORDER BY t.fecha_creacion DESC
    """, (vendedor_id,))
    transacciones = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("user/mis_transacciones.html", transacciones=transacciones)

# ---------- PÁGINA PRINCIPAL ----------
@bp.route("/pagina_principar")
@bp.route("/home")  # alias para compatibilidad con url_for("auth.home")
def home():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    categoria_filtro = request.args.get("categoria")  # puede ser None

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

    # === CARGAR CATEGORÍAS ACTIVAS ===
    cursor.execute("""
        SELECT idCategorias, nombre_categoria
        FROM categorias
        WHERE esta_activa = 1
        ORDER BY nombre_categoria
    """)
    categorias = cursor.fetchall()

    # === CONSULTA BASE PARA PUBLICACIONES ===
    base_query = """
        SELECT 
            p.idPublicaciones,
            p.titulo,
            p.descripcion,
            p.precio,
            u.nombre AS vendedor,
            i.url AS imagen_url,
            pc.id_categoria
        FROM publicaciones p
        JOIN usuarios u ON p.id_vendedor = u.idUsuarios
        LEFT JOIN imagenes_publicacion i 
            ON i.id_publicacion = p.idPublicaciones
            AND i.orden = (
                SELECT MIN(orden)
                FROM imagenes_publicacion
                WHERE id_publicacion = p.idPublicaciones
            )
        LEFT JOIN publicaciones_categoria pc
            ON pc.id_publicacion = p.idPublicaciones
        WHERE p.eliminado_en IS NULL
    """

    filtros = []
    params = []

    # Si hay categoría seleccionada ~> filtrar
    if categoria_filtro:
        filtros.append("pc.id_categoria = %s")
        params.append(categoria_filtro)

    # Cliente ve todas
    query_cliente = base_query + (" AND " + " AND ".join(filtros) if filtros else "") + " ORDER BY p.creado_en DESC"

    cursor.execute(query_cliente, params)
    publicaciones_cliente = cursor.fetchall()

    # Vendedor ve solo las suyas
    filtros_vend = filtros.copy()
    params_vend = params.copy()

    filtros_vend.append("p.id_vendedor = %s")
    params_vend.append(session["usuario_id"])

    query_vendedor = base_query + " AND " + " AND ".join(filtros_vend) + " ORDER BY p.creado_en DESC"

    cursor.execute(query_vendedor, params_vend)
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
        categorias=categorias,
        categoria_filtro=categoria_filtro,
        publicaciones_cliente=publicaciones_cliente,
        publicaciones_vendedor=publicaciones_vendedor
    )

# ---------- LOGOUT ----------
@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))