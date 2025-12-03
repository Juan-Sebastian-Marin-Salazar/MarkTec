from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.database import get_db_connection
import hashlib
import smtplib
from email.mime.text import MIMEText
import os
import random
from werkzeug.utils import secure_filename

bp = Blueprint("auth", __name__)

# ---------- VERIFICAR SI USUARIO ES ADMIN ----------
def user_is_admin(user_id):
    """
    Return True if the given user has the 'administrador' role.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM usuarios_roles ur
            JOIN roles r ON ur.id_rol = r.idRoles
            WHERE ur.id_usuario = %s AND r.nombre_rol = 'administrador'
        """, (user_id,))
        row = cursor.fetchone()
        cnt = row[0] if row else 0
        cursor.close()
        conn.close()
        return cnt > 0
    except Exception:
        return False

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

        # cargar edificios disponibles
        cursor.execute("""
            SELECT idEdificio, nombre
            FROM edificios
            WHERE esta_activa = 1
            ORDER BY nombre
        """)
        edificios = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("user/nuevo_producto.html", categorias=categorias, edificios=edificios)

    # ==== POST: Crear publicación ====
    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    precio = request.form.get("precio")
    categoria_id = request.form.get("categoria")
    edificio_id = request.form.get("edificio")
    imagenes = request.files.getlist("imagenes")
    
    if not titulo or not precio or not categoria_id or not edificio_id:
        flash("Título, precio, categoría y edificio son obligatorios.")
        return redirect(url_for("auth.nuevo_producto"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Insertar la publicación
    cursor.execute("""
        INSERT INTO publicaciones (id_vendedor, titulo, descripcion, precio, id_edificio)
        VALUES (%s, %s, %s, %s, %s)
    """, (session["usuario_id"], titulo, descripcion, precio, edificio_id))
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

# ---------- EDITAR PUBLICACIÓN (PRODUCTO) ----------
@bp.route("/editar-producto/<int:pub_id>", methods=["GET", "POST"])
def editar_producto(pub_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener la publicación y validar existencia
    cursor.execute("SELECT * FROM publicaciones WHERE idPublicaciones=%s", (pub_id,))
    producto = cursor.fetchone()

    if not producto:
        cursor.close()
        conn.close()
        return "Producto no encontrado", 404

    # Validar propietario
    if producto.get("id_vendedor") != session["usuario_id"]:
        cursor.close()
        conn.close()
        flash("No tienes permiso para editar esta publicación.")
        return redirect(url_for("auth.home"))

    # GET: mostrar formulario con datos existentes
    if request.method == "GET":
        # cargar categorias activas
        cursor.execute("""
            SELECT idCategorias, nombre_categoria
            FROM categorias
            WHERE esta_activa = 1
            ORDER BY nombre_categoria
        """)
        categorias = cursor.fetchall()

        # cargar categoria actual (si existe)
        cursor.execute("SELECT id_categoria FROM publicaciones_categoria WHERE id_publicacion=%s LIMIT 1", (pub_id,))
        cat_row = cursor.fetchone()
        categoria_actual = cat_row["id_categoria"] if cat_row else None

        # cargar imagenes
        cursor.execute("SELECT idImagenesPublicacion, url, orden FROM imagenes_publicacion WHERE id_publicacion=%s ORDER BY orden ASC", (pub_id,))
        imagenes = cursor.fetchall()

        # cargar edificios y edificio actual (si existe)
        cursor.execute("SELECT idEdificio, nombre FROM edificios WHERE esta_activa = 1 ORDER BY nombre")
        edificios = cursor.fetchall()

        edificio_actual = producto.get('id_edificio') if producto else None

        cursor.close()
        conn.close()

        return render_template(
            "user/editar_producto.html",
            producto=producto,
            categorias=categorias,
            imagenes=imagenes,
            categoria_actual=categoria_actual,
            edificios=edificios,
            edificio_actual=edificio_actual
        )

    # POST: guardar cambios
    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    precio = request.form.get("precio")
    categoria_id = request.form.get("categoria")
    edificio_id = request.form.get("edificio")
    imagenes_nuevas = request.files.getlist("imagenes")
    imagenes_a_eliminar = request.form.getlist("imagenes_a_eliminar")

    if not titulo or not precio or not categoria_id or not edificio_id:
        flash("Título, precio, categoría y edificio son obligatorios.")
        return redirect(url_for("auth.editar_producto", pub_id=pub_id))

    # Procesar eliminación de imágenes marcadas
    for img_id in imagenes_a_eliminar:
        cursor.execute("SELECT url FROM imagenes_publicacion WHERE idImagenesPublicacion=%s AND id_publicacion=%s", (img_id, pub_id))
        img_row = cursor.fetchone()
        if img_row:
            # Borrar fila
            cursor.execute("DELETE FROM imagenes_publicacion WHERE idImagenesPublicacion=%s", (img_id,))
            
            # Si no hay otros registros con la misma URL, eliminar el archivo físico
            url = img_row.get("url")
            cursor.execute("SELECT COUNT(*) AS cnt FROM imagenes_publicacion WHERE url=%s", (url,))
            cnt_row = cursor.fetchone()
            cnt = cnt_row.get("cnt") if cnt_row else 0
            
            if cnt == 0 and url:
                filename = os.path.basename(url)
                path = os.path.join(os.getcwd(), "app", "static", "uploads", filename)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
    
    conn.commit()

    # Actualizar publicación
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE publicaciones
        SET titulo=%s, descripcion=%s, precio=%s, id_edificio=%s
        WHERE idPublicaciones=%s
    """, (titulo, descripcion, precio, edificio_id, pub_id))
    conn.commit()

    # Reemplazar categoría (simple enfoque: borrar y volver a insertar)
    cursor.execute("DELETE FROM publicaciones_categoria WHERE id_publicacion=%s", (pub_id,))
    cursor.execute("INSERT INTO publicaciones_categoria (id_publicacion, id_categoria) VALUES (%s, %s)", (pub_id, categoria_id))
    conn.commit()

    # Guardar nuevas imágenes (si se suben)
    if imagenes_nuevas:
        uploads_dir = os.path.join(os.getcwd(), "app", "static", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        # determine current max orden to append
        cursor.execute("SELECT COALESCE(MAX(orden), -1) AS maxorden FROM imagenes_publicacion WHERE id_publicacion=%s", (pub_id,))
        row = cursor.fetchone()
        start_index = row[0] + 1 if row and isinstance(row[0], int) else 0

        for i, img in enumerate(imagenes_nuevas):
            if img and img.filename:
                filename = secure_filename(img.filename)
                ruta_absoluta = os.path.join(uploads_dir, filename)
                img.save(ruta_absoluta)

                url_imagen = f"/static/uploads/{filename}"

                # Avoid inserting duplicate image rows for the same URL
                cursor.execute("SELECT COUNT(*) FROM imagenes_publicacion WHERE id_publicacion=%s AND url=%s", (pub_id, url_imagen))
                exists = cursor.fetchone()[0]
                if exists == 0:
                    cursor.execute("""
                        INSERT INTO imagenes_publicacion (id_publicacion, url, texto_alternativo, orden)
                        VALUES (%s, %s, %s, %s)
                    """, (pub_id, url_imagen, titulo, start_index + i))
                else:
                    # skip duplicate
                    pass
        conn.commit()

    cursor.close()
    conn.close()

    flash("Tu publicación ha sido actualizada correctamente.")
    return redirect(url_for("auth.detalle_producto", pub_id=pub_id))

# ---------- DETALLE PUBLICACIÓN (PRODUCTO) ----------
@bp.route("/producto/<int:pub_id>")
def detalle_producto(pub_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener datos del producto (incluye telefono del vendedor y nombre de edificio si existe)
    cursor.execute("""
        SELECT p.*, u.nombre AS vendedor, u.telefono AS telefono_vendedor, e.nombre AS edificio_nombre
        FROM publicaciones p
        JOIN usuarios u ON p.id_vendedor = u.idUsuarios
        LEFT JOIN edificios e ON p.id_edificio = e.idEdificio
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

# ---------- ELIMINAR IMAGEN DE PUBLICACIÓN ----------
@bp.route("/eliminar-imagen/<int:img_id>", methods=["POST"]) 
def eliminar_imagen(img_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener la imagen y la publicacion asociada
    cursor.execute("SELECT idImagenesPublicacion, id_publicacion, url FROM imagenes_publicacion WHERE idImagenesPublicacion=%s", (img_id,))
    img = cursor.fetchone()

    if not img:
        cursor.close()
        conn.close()
        flash("Imagen no encontrada.")
        return redirect(url_for("auth.home"))

    pub_id = img.get("id_publicacion")

    # validar propietario de la publicacion
    cursor.execute("SELECT id_vendedor FROM publicaciones WHERE idPublicaciones=%s", (pub_id,))
    pub = cursor.fetchone()
    if not pub or pub.get("id_vendedor") != session["usuario_id"]:
        cursor.close()
        conn.close()
        flash("No tienes permiso para eliminar esta imagen.")
        return redirect(url_for("auth.home"))

    # borrar fila de imagen
    cursor.execute("DELETE FROM imagenes_publicacion WHERE idImagenesPublicacion=%s", (img_id,))
    conn.commit()

    # si ningun otro registro referencia el mismo archivo, eliminar archivo fisico
    url = img.get("url")
    cursor.execute("SELECT COUNT(*) AS cnt FROM imagenes_publicacion WHERE url=%s", (url,))
    row = cursor.fetchone()
    cnt = row.get("cnt") if row and isinstance(row, dict) else (row[0] if row else 0)

    if cnt == 0 and url:
        filename = os.path.basename(url)
        path = os.path.join(os.getcwd(), "app", "static", "uploads", filename)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    cursor.close()
    conn.close()

    flash("Imagen eliminada correctamente.")
    return redirect(url_for("auth.editar_producto", pub_id=pub_id))

# ---------- ELIMINAR PUBLICACIÓN ----------
@bp.route("/eliminar-producto/<int:pub_id>", methods=["POST"])
def eliminar_producto(pub_id):
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    # Validar que la publicación pertenece al usuario actual y marcar como eliminada
    cursor.execute("""
        UPDATE publicaciones
        SET eliminado_en = NOW()
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

# ------------------ ADMIN INTERFACE (restricted) ------------------
@bp.route('/admin')
def admin():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    return render_template('admin/admin.html')

# ---------- ADMIN: LISTA DE EDIFICIOS ----------
@bp.route('/admin/edificios')
def admin_edificios():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    edificios = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT idEdificio, nombre, descripcion, esta_activa FROM edificios ORDER BY idEdificio ASC')
        edificios = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        edificios = []

    return render_template('admin/lista_edificio.html', edificios=edificios)

# ---------- ADMIN: LISTA DE USUARIOS ----------
@bp.route('/admin/usuarios')
def admin_usuarios():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    usuarios = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.idUsuarios, u.nombre, u.correo, u.matricula, u.eliminado_en,
                   (SELECT GROUP_CONCAT(r.nombre_rol SEPARATOR ', ') FROM usuarios_roles ur JOIN roles r ON ur.id_rol = r.idRoles WHERE ur.id_usuario = u.idUsuarios) AS rol
            FROM usuarios u
            ORDER BY u.idUsuarios ASC
        """)
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        usuarios = []

    return render_template('admin/lista_usuarios.html', usuarios=usuarios)

# ---------- ADMIN: LISTA DE CATEGORÍAS ----------
@bp.route('/admin/categorias')
def admin_categorias():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    categorias = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT idCategorias, nombre_categoria, esta_activa FROM categorias ORDER BY idCategorias ASC')
        categorias = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        categorias = []

    return render_template('admin/lista_categorias.html', categorias=categorias)

# ---------- ADMIN: CREAR EDIFICIO ----------
@bp.route('/admin/edificios/nuevo', methods=['GET', 'POST'])
def admin_edificio_nuevo():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    if request.method == 'GET':
        return render_template('admin/form_edificio.html', edificio=None)

    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    esta_activa = 1 if request.form.get('esta_activa') == 'on' else 0

    if not nombre:
        flash('El nombre es obligatorio.')
        return redirect(url_for('auth.admin_edificio_nuevo'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO edificios (nombre, descripcion, esta_activa) VALUES (%s, %s, %s)', (nombre, descripcion, esta_activa))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Edificio creado correctamente.')
    return redirect(url_for('auth.admin_edificios'))


# ---------- ADMIN: EDITAR EDIFICIO ----------
@bp.route('/admin/edificios/editar/<int:id>', methods=['GET', 'POST'])
def admin_edificio_editar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT idEdificio, nombre, descripcion, esta_activa FROM edificios WHERE idEdificio=%s', (id,))
    ed = cursor.fetchone()

    if not ed:
        cursor.close()
        conn.close()
        flash('Edificio no encontrado.')
        return redirect(url_for('auth.admin_edificios'))

    if request.method == 'GET':
        cursor.close()
        conn.close()
        return render_template('admin/form_edificio.html', edificio=ed)

    # POST: actualizar
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    esta_activa = 1 if request.form.get('esta_activa') == 'on' else 0

    if not nombre:
        flash('El nombre es obligatorio.')
        return redirect(url_for('auth.admin_edificio_editar', id=id))

    cursor.execute('UPDATE edificios SET nombre=%s, descripcion=%s, esta_activa=%s WHERE idEdificio=%s', (nombre, descripcion, esta_activa, id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Edificio actualizado.')
    return redirect(url_for('auth.admin_edificios'))


# ---------- ADMIN: ELIMINAR EDIFICIO (soft) ----------
@bp.route('/admin/edificios/eliminar/<int:id>', methods=['POST'])
def admin_edificio_eliminar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE edificios SET esta_activa = 0 WHERE idEdificio=%s', (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Edificio desactivado.')
    return redirect(url_for('auth.admin_edificios'))


# ---------- ADMIN: CREAR CATEGORIA ----------
@bp.route('/admin/categorias/nuevo', methods=['GET', 'POST'])
def admin_categoria_nuevo():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    if request.method == 'GET':
        return render_template('admin/form_categoria.html', categoria=None)

    nombre = request.form.get('nombre')
    esta_activa = 1 if request.form.get('esta_activa') == 'on' else 0

    if not nombre:
        flash('El nombre es obligatorio.')
        return redirect(url_for('auth.admin_categoria_nuevo'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO categorias (nombre_categoria, id_creador, esta_activa) VALUES (%s, NULL, %s)', (nombre, esta_activa))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Categoría creada correctamente.')
    return redirect(url_for('auth.admin_categorias'))


# ---------- ADMIN: EDITAR CATEGORIA ----------
@bp.route('/admin/categorias/editar/<int:id>', methods=['GET', 'POST'])
def admin_categoria_editar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT idCategorias, nombre_categoria, esta_activa FROM categorias WHERE idCategorias=%s', (id,))
    c = cursor.fetchone()

    if not c:
        cursor.close()
        conn.close()
        flash('Categoría no encontrada.')
        return redirect(url_for('auth.admin_categorias'))

    if request.method == 'GET':
        cursor.close()
        conn.close()
        return render_template('admin/form_categoria.html', categoria=c)

    nombre = request.form.get('nombre')
    esta_activa = 1 if request.form.get('esta_activa') == 'on' else 0

    if not nombre:
        flash('El nombre es obligatorio.')
        return redirect(url_for('auth.admin_categoria_editar', id=id))

    cursor.execute('UPDATE categorias SET nombre_categoria=%s, esta_activa=%s WHERE idCategorias=%s', (nombre, esta_activa, id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Categoría actualizada.')
    return redirect(url_for('auth.admin_categorias'))


# ---------- ADMIN: ELIMINAR CATEGORIA (soft) ----------
@bp.route('/admin/categorias/eliminar/<int:id>', methods=['POST'])
def admin_categoria_eliminar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE categorias SET esta_activa = 0 WHERE idCategorias=%s', (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Categoría desactivada.')
    return redirect(url_for('auth.admin_categorias'))


# ---------- ADMIN: ELIMINAR USUARIO ----------
@bp.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
def admin_usuario_eliminar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuarios SET eliminado_en = NOW() WHERE idUsuarios=%s', (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Usuario marcado como eliminado.')
    return redirect(url_for('auth.admin_usuarios'))


# ---------- ADMIN: CREAR USUARIO ----------
@bp.route('/admin/usuarios/nuevo', methods=['GET', 'POST'])
def admin_usuario_nuevo():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    if request.method == 'GET':
        return render_template('admin/form_usuario.html', usuario=None)

    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    matricula = request.form.get('matricula')
    password = request.form.get('password')

    if not nombre or not correo:
        flash('Nombre y correo son obligatorios.')
        return redirect(url_for('auth.admin_usuario_nuevo'))

    clave_hash = None
    if password:
        clave_hash = hashlib.sha256(password.encode()).hexdigest()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if clave_hash:
            cursor.execute('INSERT INTO usuarios (nombre, correo, matricula, clave_hash) VALUES (%s, %s, %s, %s)', (nombre, correo, matricula, clave_hash))
        else:
            cursor.execute('INSERT INTO usuarios (nombre, correo, matricula, clave_hash) VALUES (%s, %s, %s, %s)', (nombre, correo, matricula, ''))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al crear usuario: {e}')
        return redirect(url_for('auth.admin_usuario_nuevo'))

    flash('Usuario creado correctamente.')
    return redirect(url_for('auth.admin_usuarios'))


# ---------- ADMIN: EDITAR USUARIO ----------
@bp.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def admin_usuario_editar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    if not user_is_admin(session['usuario_id']):
        flash('Acceso denegado: se requieren permisos de administrador.')
        return redirect(url_for('auth.home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT idUsuarios, nombre, correo, matricula FROM usuarios WHERE idUsuarios=%s', (id,))
    u = cursor.fetchone()

    if not u:
        cursor.close()
        conn.close()
        flash('Usuario no encontrado.')
        return redirect(url_for('auth.admin_usuarios'))

    if request.method == 'GET':
        cursor.close()
        conn.close()
        return render_template('admin/form_usuario.html', usuario=u)

    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    matricula = request.form.get('matricula')
    password = request.form.get('password')

    if not nombre or not correo:
        flash('Nombre y correo son obligatorios.')
        return redirect(url_for('auth.admin_usuario_editar', id=id))

    try:
        if password:
            clave_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('UPDATE usuarios SET nombre=%s, correo=%s, matricula=%s, clave_hash=%s WHERE idUsuarios=%s', (nombre, correo, matricula, clave_hash, id))
        else:
            cursor.execute('UPDATE usuarios SET nombre=%s, correo=%s, matricula=%s WHERE idUsuarios=%s', (nombre, correo, matricula, id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error al actualizar usuario: {e}')
        return redirect(url_for('auth.admin_usuario_editar', id=id))

    flash('Usuario actualizado.')
    return redirect(url_for('auth.admin_usuarios'))

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