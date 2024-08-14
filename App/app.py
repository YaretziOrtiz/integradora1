from flask import Flask, render_template, url_for, redirect, request, flash
import os
import uuid 
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect 

from werkzeug.security import generate_password_hash
from flask_login import LoginManager, login_user, login_required, current_user, logout_user

from Models.ModelUser import ModelUser
from Models.entities.user import User 


app= Flask(__name__)
csrf= CSRFProtect()

#conexion con base de datos
def get_db_connection():
    try:
        conn = psycopg2.connect(host='localhost',
                                dbname='nutrimentosRolkar',
                                user=os.environ['DB_USERNAME'],
                                password=os.environ['DB_PASSWORD'])                   
        return conn
    except psycopg2.Error as error:
        print(f"Error al conectar la base de datos:{error}")
        return None

Login_manager_app=LoginManager(app)

@Login_manager_app.user_loader
def load_user(idusuarios):
    return ModelUser.get_by_id(get_db_connection(),idusuarios)

def listar_categorias():
    conn = get_db_connection() 
    cur = conn.cursor()
    cur.execute('SELECT * FROM categorias ORDER BY id_categoria ASC;')
    categorias = cur.fetchall()
    cur.close()
    conn.close()
    return categorias

def listar_proveedores():
    conn = get_db_connection() 
    cur = conn.cursor()
    cur.execute('SELECT * FROM proveedor ORDER BY id_proveedor ASC;')
    proveedores = cur.fetchall()
    cur.close()
    conn.close()
    return proveedores

app.secret_key='mysecretkey'

@app.route("/")
@login_required
def inicioSesion():
    return render_template('login.html')

#---------------------PAGINADOR-------------
def paginador(sql_count: str, sql_lim: str, search_query: str, in_page: int, per_pages: int) -> tuple[list[dict], int, int, int, int]:
    page = request.args.get('page', in_page, type=int)
    per_page = request.args.get('per_page', per_pages, type=int)

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1

    offset = (page - 1) * per_page

    try:
         conn = get_db_connection()
         cursor = conn.cursor(cursor_factory=RealDictCursor)
    
         cursor.execute(sql_count, (f"%{search_query}%",f"%{search_query}%"))
         total_items = cursor.fetchone()['count']

         cursor.execute(sql_lim, (f"%{search_query}%",f"%{search_query}%", per_page, offset))
         items = cursor.fetchall()

    except psycopg2.Error as e:
        print(f"Error en la base de datos: {e}")
        items = []
        total_items = 0
    finally:
        # Asegurar el cierre de la conexión
        cursor.close()
        conn.close()


    total_pages = (total_items + per_page - 1) // per_page

    return items, page, per_page, total_items, total_pages

#------------------------- Tiempo -------------------------
@app.template_filter('formatear_tiempo')
def formatear_tiempo(fecha_pasada):
    ahora = datetime.now()
    diferencia = relativedelta(ahora, fecha_pasada)

    if diferencia.years > 0:
        return f"Hace {diferencia.years} años"
    elif diferencia.years == 1:
        return f"Hace {diferencia.years} año"
    elif diferencia.months > 0:
        return f"Hace {diferencia.months} meses"
    elif diferencia.months == 1:
        return f"Hace {diferencia.months} mes"
    elif diferencia.days > 0:
        return f"Hace {diferencia.days} días"
    elif diferencia.days == 1:
        return f"Hace {diferencia.days} día"
    elif diferencia.hours > 0:
        return f"Hace {diferencia.hours} horas"
    elif diferencia.hours == 1:
        return f"Hace {diferencia.hours} hora"
    elif diferencia.minutes > 0:
        return f"Hace {diferencia.minutes} minutos"
    elif diferencia.minutes == 1:
        return f"Hace {diferencia.minutes} minuto"
    else:
        return "Hace unos segundos"

#----------------------PRODUCTOS------------------------------------

@app.route("/dashboard_productos")
@login_required
def dashboardProductos():
    titulo = "Productos"
    search_query = request.args.get('buscar', '', type=str)
    sql_count = 'SELECT COUNT(*) FROM vista_productos WHERE nombre_producto ILIKE %s OR marca ILIKE %s'
    sql_lim = 'SELECT * FROM vista_productos WHERE nombre_producto ILIKE %s OR marca ILIKE %s LIMIT %s OFFSET %s'
    paginado = paginador(sql_count, sql_lim, search_query, 1, 10)
    return render_template('dashboardProductos.html', titulo=titulo,
                            productos=paginado[0],
                            page=paginado[1],
                            per_page=paginado[2],
                            total_items=paginado[3],
                            total_pages=paginado[4],
                            search_query=search_query)

@app.route("/productos_nuevo")
@login_required
def productosNuevo():
    return render_template('productosNuevo.html', categorias=listar_categorias(),proveedores=listar_proveedores())

@app.route('/dashboard/productos/crear', methods=('GET', 'POST'))
@login_required
def productosCrear():
    if request.method == 'POST':
        nombre = request.form['nombre']
        marca = request.form['marca']
        precio = request.form['precio']
        fecha_caducidad = request.form['fecha_caducidad']
        proveedor = request.form['id_proveedor']
        categoria = request.form['id_categoria']
        activo = True
        creado = datetime.now()
        editado = datetime.now()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO productos (nombre, marca, precio, fecha_cad, fk_proveedor, fk_categoria)'
                    'VALUES (%s, %s, %s, %s, %s, %s)',
                    (nombre, marca, precio,fecha_caducidad, proveedor, categoria))
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Producto agregado exitosamente!')

        return redirect(url_for('dashboardProductos'))

    return redirect(url_for('productosNuevo'))


@app.route("/productos_categoria")
@login_required
def productosCategoria():
    return render_template('productosCategoria.html')

@app.route("/productos_editar/<string:id>")
@login_required
def productosEditar(id):
    titulo = "Editar Producto"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM productos WHERE id_producto={0}'.format(id))
    producto=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('productosEditar.html', titulo=titulo, producto=producto[0], categorias=listar_categorias(), proveedores=listar_proveedores())

@app.route('/dashboard/productos/actualizar/<string:id>', methods=['POST'])
@login_required
def productosActualizar(id):
    if request.method == 'POST':
        nombre = request.form['nombre']
        marca = request.form['marca']
        precio = request.form['precio']
       # categoria = request.form['categoria']
        fecha_caducidad = request.form['fecha_caducidad']

        conn = get_db_connection()
        cur = conn.cursor()
        sql="UPDATE productos SET nombre=%s, marca=%s, precio=%s, fecha_cad=%s WHERE id_producto=%s"        
        valores=(nombre, marca, precio, fecha_caducidad, id)
        cur.execute(sql,valores)
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Producto actualizado exitosamente!')

        return redirect(url_for('dashboardProductos'))

@app.route('/dashboard/productos/eliminar/<string:id>')
@login_required
def productoEliminar(id):
    #activo = False
    #editado = datetime.now()
    conn = get_db_connection()
    cur = conn.cursor()
    sql="DELETE FROM productos WHERE id_producto={0}".format(id)
    #sql="UPDATE productos SET activo=%s WHERE id_producto=%s"
    valores=(id)
    cur.execute(sql,valores)
    conn.commit()
    cur.close()
    conn.close()
    flash('¡Producto eliminado correctamente!')
    return redirect(url_for('dashboardProductos'))


@app.route("/productos_detalles/<string:id>")
@login_required
def productosDetalles(id):
    titulo="Detalles Producto"
    conn= get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM productos WHERE id_producto = {0}'.format(id))
    producto=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    #hora_actual=datetime.now()
    return render_template('productosDetalles.html', titulo=titulo, producto=producto[0])

#-----------------------PROVEEDORES-----------------------------------------------------
@app.route("/dashboard_proveedores")
@login_required
def dashboardProveedores():
    titulo = "Proveedores"
    search_query = request.args.get('buscar', '', type=str)
    sql_count = 'SELECT COUNT(*) FROM proveedor WHERE activo=true AND (nombre ILIKE %s OR ape_pat ILIKE %s); '
    sql_lim = 'SELECT * FROM proveedor  WHERE activo=true AND (nombre ILIKE %s OR ape_pat ILIKE %s) ORDER BY id_proveedor DESC  LIMIT %s OFFSET %s;'
    paginado = paginador(sql_count, sql_lim, search_query, 1, 10)
    print('provedores')
    print(paginado[0])

    print('page')
    print(paginado[1])

    print('pp')
    print(paginado[2])

    print('total')
    print(paginado[3])

    print('total p')
    print(paginado[4])
    return render_template('dashboardProveedores.html', titulo=titulo,
                            proveedores=paginado[0],
                            page=paginado[1],
                            per_page=paginado[2],
                            total_items=paginado[3],
                            total_pages=paginado[4],
                            search_query=search_query)

@app.route("/proveedor_nuevo")
@login_required
def proveedorNuevo():
    return render_template('proveedoresNuevo.html')

@app.route('/dashboard/proveedores/crear', methods=('GET', 'POST'))
@login_required
def proveedoresCrear():
    if request.method == 'POST':
        nombre = request.form['nombre']
        paterno = request.form['paterno']
        materno = request.form['materno']
        marca = request.form['marca']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        correo = request.form['correo']
        cp = request.form['cp']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO proveedor (nombre, ape_pat, ape_mat, marca, telefono, direccion, correo, cp)'
                    'VALUES ( %s, %s, %s, %s, %s, %s, %s, %s)',
                    ( nombre, paterno, materno, marca, telefono, direccion, correo, cp))
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Proveedor agregado exitosamente!')

        return redirect(url_for('dashboardProveedores'))

    return redirect(url_for('proveedoresNuevo'))

@app.route("/proveedores_editar/<string:id>")
@login_required
def proveedoresEditar(id):
    titulo = "Editar Proveedor"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM proveedor WHERE id_proveedor={0}'.format(id))
    proveedores=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('proveedoresEditar.html', titulo=titulo, proveedor=proveedores[0])

@app.route('/dashboard/proveedores/actualizar/<string:id>', methods=['POST'])
@login_required
def proveedoresActualizar(id):
    if request.method == 'POST':
        id_proveedor=request.form['id_proveedor']
        nombre = request.form['nombre']
        paterno = request.form['paterno']
        materno = request.form['materno']
        marca = request.form['marca']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        correo = request.form['correo']
        cp = request.form['cp']


        conn = get_db_connection()
        cur = conn.cursor()
        sql="UPDATE proveedor SET nombre=%s, ape_pat=%s, ape_mat=%s, marca=%s,  telefono=%s, direccion=%s, correo=%s, cp=%s WHERE id_proveedor=%s"        
        valores=( nombre, paterno, materno, marca, telefono, direccion, correo, cp, id_proveedor)
        cur.execute(sql,valores)
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Proveedor actualizado exitosamente!')

        return redirect(url_for('dashboardProveedores'))
    
@app.route("/proveedores_detalles/<string:id>")
@login_required
def proveedoresDetalles(id):
    titulo="Detalles proveedor"
    conn= get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM proveedor WHERE id_proveedor = {0}'.format(id))
    proveedor=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('proveedoresDetalles.html', titulo=titulo, proveedor=proveedor[0])

@app.route('/dashboard/proveedores/eliminar/<string:id>')
@login_required
def proveedorEliminar(id):
    #activo = False
    #editado = datetime.now()
    conn = get_db_connection()
    cur = conn.cursor()
    sql="DELETE FROM proveedor WHERE id_proveedor={0}".format(id)
    #sql="UPDATE productos SET activo=%s WHERE id_producto=%s"
    valores=(id)
    cur.execute(sql,valores)
    conn.commit()
    cur.close()
    conn.close()
    flash('¡Proveedor eliminado correctamente!')
    return redirect(url_for('dashboardProveedores'))

#--------------------USUARIOS---------------------------------------------------------------------
@app.route("/dashboard_usuarios")
@login_required
def dashboardUsuarios():
    titulo = "Usuarios"
    search_query = request.args.get('buscar', '', type=str)
    sql_count = 'SELECT COUNT(*) FROM usuarios WHERE activo=True AND (username ILIKE %s OR tipo_usuario ILIKE %s); '
    sql_lim = 'SELECT * FROM usuarios  WHERE activo=true AND (username ILIKE %s OR tipo_usuario ILIKE %s) ORDER BY id_usuario DESC LIMIT %s OFFSET %s;'
    paginado = paginador(sql_count, sql_lim, search_query, 1, 10)
    print('usuarios')
    print(paginado[0])

    print('page')
    print(paginado[1])

    print('pp')
    print(paginado[2])

    print('total')
    print(paginado[3])

    print('total p')
    print(paginado[4])
    return render_template('dashboardUsuarios.html', titulo=titulo,
   
                            usuarios=paginado[0],
                            page=paginado[1],
                            per_page=paginado[2],
                            total_items=paginado[3],
                            total_pages=paginado[4],
                            search_query=search_query)

@app.route("/usuarios_nuevo")
@login_required
def registrarUsuario():
    return render_template('registrarUsuario.html')

@app.route('/dashboard/usuarios/crear', methods=('GET', 'POST'))
@login_required
def usuariosCrear():
    if request.method == 'POST' and current_user.tipo == True:
        username = request.form['username']
        password = request.form['password']
        tipo_usuario = request.form['tipo_usuario']
        activo = True
       

        # Hashear la contraseña antes de almacenarla
        #hashed_password = generate_password_hash(contrasenia)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO usuarios (username, password, tipo_usuario, activo)'
                    'VALUES (%s, %s, %s, %s)',
                    (username, password, tipo_usuario, activo))
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Usuario agregado exitosamente!')

        return redirect(url_for('dashboardUsuarios'))

    return redirect(url_for('registrarUsuario'))


@app.route("/usuarios_editar/<string:id>")
@login_required
def usuariosEditar(id):
    titulo = "Editar Usuario"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id_usuario=%s', (id,))
    usuario = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('usuariosEditar.html', titulo=titulo, usuario=usuario)


@app.route('/dashboard/usuarios/actualizar/<string:id>', methods=['POST'])
@login_required
def usuariosActualizar(id):
    if request.method == 'POST':
        id_usuario=request.form['id_usuario']
        nombre = request.form['nombre']
        paterno = request.form['paterno']
        materno = request.form['materno']
        direccion = request.form['direccion']
        telefono = request.form['telefono']
        correo = request.form['correo']
        rol = request.form['rol']
        


        conn = get_db_connection()
        cur = conn.cursor()
        sql="UPDATE usuarios SET nombre=%s, ape_pat=%s, ape_mat=%s, direccion=%s, telefono=%s , correo=%s, rol=%s WHERE id_usuario=%s"        
        valores=( nombre, paterno, materno, direccion, telefono, correo, rol, id_usuario)
        cur.execute(sql,valores)
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Usuario actualizado exitosamente!')

        return redirect(url_for('dashboardUsuarios'))
    
@app.route("/usuarios_detalles/<string:id>")
@login_required
def usuariosDetalles(id):
    titulo="Detalles usuario"
    conn= get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id_usuario = {0}'.format(id))
    usuario=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    #hora_actual=datetime.now()
    return render_template('usuariosDetalles.html', titulo=titulo, usuario=usuario[0])

@app.route('/dashboard/usuarios/eliminar/<string:id>')
@login_required
def usuarioEliminar(id):
    #activo = False
    #editado = datetime.now()
    conn = get_db_connection()
    cur = conn.cursor()
    sql="DELETE FROM usuarios WHERE id_usuario={0}".format(id)
    #sql="UPDATE productos SET activo=%s WHERE id_producto=%s"
    valores=(id)
    cur.execute(sql,valores)
    conn.commit()
    cur.close()
    conn.close()
    flash('¡Usuario eliminado correctamente!')
    return redirect(url_for('dashboardUsuarios'))

#-------------------------------Clientes-------------------------------------------
@app.route("/dashboard_clientes")
@login_required
def dashboardCliente():
    titulo = "Clientes"
    search_query = request.args.get('buscar', '', type=str)
    sql_count = 'SELECT COUNT(*) FROM cliente WHERE activo=True AND (nombre ILIKE %s OR ape_pat ILIKE %s); '
    sql_lim = 'SELECT * FROM cliente  WHERE activo=true AND (nombre ILIKE %s OR ape_pat ILIKE %s) ORDER BY id_cliente DESC  LIMIT %s OFFSET %s;'
    paginado = paginador(sql_count, sql_lim, search_query, 1, 10)
    print('clientes')
    print(paginado[0])

    print('page')
    print(paginado[1])

    print('pp')
    print(paginado[2])

    print('total')
    print(paginado[3])

    print('total p')
    print(paginado[4])
    return render_template('dashboardCliente.html', titulo=titulo,
                            clientes=paginado[0],
                            page=paginado[1],
                            per_page=paginado[2],
                            total_items=paginado[3],
                            total_pages=paginado[4],
                            search_query=search_query)

@app.route("/cliente_nuevo")
@login_required
def clienteNuevo():
    return render_template('clienteNuevo.html')

@app.route('/dashboard/cliente/crear', methods=('GET', 'POST'))
@login_required
def clienteCrear():
    if request.method == 'POST':
        nombre = request.form['nombre']
        paterno = request.form['paterno']
        materno = request.form['materno']
        direccion = request.form['direccion']
        telefono = request.form['telefono']
        correo = request.form['correo']
        cp = request.form['cp']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO cliente (nombre, ape_pat, ape_mat, direccion, telefono, correo, cp)'
                    'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (nombre, paterno, materno, direccion, telefono, correo, cp))
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Cliente agregado exitosamente!')

        return redirect(url_for('dashboardCliente'))

    return redirect(url_for('clienteNuevo'))

@app.route("/cliente_editar/<string:id>")
@login_required
def clienteEditar(id):
    titulo = "Editar Cliente"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM cliente WHERE id_cliente={0}'.format(id))
    cliente=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('clienteEditar.html', titulo=titulo, cliente=cliente[0])

@app.route('/dashboard/cliente/actualizar/<string:id>', methods=['POST'])
@login_required
def clienteActualizar(id):
    if request.method == 'POST':
        nombre = request.form['nombre']
        paterno = request.form['paterno']
        materno = request.form['materno']
        direccion = request.form['direccion']
        telefono = request.form['telefono']
        correo = request.form['correo']
        cp = request.form['cp']
        


        conn = get_db_connection()
        cur = conn.cursor()
        sql="UPDATE cliente SET nombre=%s, ape_pat=%s, ape_mat=%s, direccion=%s, telefono=%s , correo=%s, cp=%s WHERE id_cliente=%s"        
        valores=( nombre, paterno, materno, direccion, telefono, correo, cp, id)
        cur.execute(sql,valores)
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Cliente actualizado exitosamente!')

        return redirect(url_for('dashboardCliente'))
    
@app.route("/cliente_detalles/<string:id>")
@login_required
def clienteDetalles(id):
    titulo="Detalles cliente"
    conn= get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM cliente WHERE id_cliente = {0}'.format(id))
    cliente=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    #hora_actual=datetime.now()
    return render_template('clienteDetalles.html', titulo=titulo, cliente=cliente[0])

@app.route('/dashboard/cliente/eliminar/<string:id>')
@login_required
def clienteEliminar(id):
    #activo = False
    #editado = datetime.now()
    conn = get_db_connection()
    cur = conn.cursor()
    sql="DELETE FROM cliente WHERE id_cliente={0}".format(id)
    #sql="UPDATE productos SET activo=%s WHERE id_producto=%s"
    valores=(id)
    cur.execute(sql,valores)
    conn.commit()
    cur.close()
    conn.close()
    flash('¡Cliente eliminado correctamente!')
    return redirect(url_for('dashboardClientes'))

#-----------------Categoria--------------------------

@app.route("/dashboard_categorias")
@login_required
def dashboardCategorias():
    titulo = "Categorias"
    search_query = request.args.get('buscar', '', type=str)
    sql_count = 'SELECT COUNT(*) FROM categorias WHERE activo=True AND (especie ILIKE %s OR tipo ILIKE %s); '
    sql_lim = 'SELECT * FROM categorias  WHERE activo=true AND (especie ILIKE %s OR tipo ILIKE %s) ORDER BY id_categoria DESC  LIMIT %s OFFSET %s;'
    paginado = paginador(sql_count, sql_lim, search_query, 1, 10)
    return render_template('dashboardCategorias.html', titulo=titulo,
                            categorias=paginado[0],
                            page=paginado[1],
                            per_page=paginado[2],
                            total_items=paginado[3],
                            total_pages=paginado[4],
                            search_query=search_query)
    
@app.route("/categorias_nuevo")
@login_required
def categoriasNuevo():
    return render_template('categoriasNuevo.html')

@app.route('/dashboard/categorias/crear', methods=('GET', 'POST'))
@login_required
def categoriasCrear():
    if request.method == 'POST':
        especie = request.form['especie']
        tipo= request.form['tipo']
        presentacion= request.form['presentacion']
        activo= True
    

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO categorias (especie, tipo, presentacion, activo)'
                    'VALUES (%s, %s, %s, %s)',
                    (especie, tipo, presentacion, activo))
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Categoria agregada exitosamente!')

        return redirect(url_for('dashboardCategorias'))

    return redirect(url_for('categoriasNuevo'))

@app.route("/categorias_editar/<string:id>")
@login_required
def categoriasEditar(id):
    titulo = "Editar Categoria"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM categorias WHERE id_categoria={0}'.format(id))
    categoria=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return render_template('categoriasEditar.html', titulo=titulo, categoria=categoria[0])

@app.route('/dashboard/categorias/actualizar/<string:id>', methods=['POST'])
@login_required
def categoriasActualizar(id):
    if request.method == 'POST':
        especie = request.form['especie']
        tipo= request.form['tipo']
        presentacion= request.form['presentacion']


        conn = get_db_connection()
        cur = conn.cursor()
        sql="UPDATE categorias SET especie=%s, tipo=%s, presentacion=%s WHERE id_categoria=%s"        
        valores=( especie, tipo, presentacion, id)
        cur.execute(sql,valores)
        conn.commit()
        cur.close()
        conn.close()

        flash('¡Categoria actualizado exitosamente!')

        return redirect(url_for('dashboardCategorias'))
    
@app.route("/categorias_detalles/<string:id>")
@login_required
def categoriasDetalles(id):
    titulo="Detalles categoria"
    conn= get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM categorias WHERE id_categoria = {0}'.format(id))
    categoria=cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    #hora_actual=datetime.now()
    return render_template('categoriasDetalles.html', titulo=titulo, categoria=categoria[0])

@app.route('/dashboard/categoria/eliminar/<string:id>')
@login_required
def categoriaEliminar(id):
    activo = True
    #editado = datetime.now()
    conn = get_db_connection()
    cur = conn.cursor()
    sql="DELETE FROM categorias WHERE id_categoria={0}".format(id)
    #sql="UPDATE productos SET activo=%s WHERE id_producto=%s"
    valores=(id)
    cur.execute(sql,valores)
    conn.commit()
    cur.close()
    conn.close()
    flash('¡Categoria eliminado correctamente!')
    return redirect(url_for('dashboardCategorias'))

#-----------------------CAJERO---------------------------------------
@app.route('/cajero/ventas')
@login_required
def cajeroVentas():
    return render_template('cajeroVentas.html')

@app.route('/cajero/corte')
@login_required
def cajeroCorte():
    return render_template('cajeroCorte.html')

@app.route('/cajero/gastos')
@login_required
def cajeroGastos():
    return render_template('cajeroGastos.html')

#---------------LOGIN--------------------
@app.route('/login')
def login():
    return render_template('/login.html')

@app.route('/loguear', methods=('GET', 'POST'))
def loguear():
    if request.method == 'POST':
        username=request.form['username']
        password=request.form['password']
        user=User(0,username,password,None,None,None,None)
        loged_user = ModelUser.login(get_db_connection(),user)

        if loged_user!=None:
            if loged_user.password:
                login_user(loged_user)
                return redirect(url_for('dashboardProductos'))
            else:
                flash("Nombre de usuario y/o contraseña incorrecta.")
                return redirect(url_for('login'))
        else:
            flash("Nombre de usuario y/o conttraseña incorrecta.")
            return redirect(url_for('login'))
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def pagina_no_encontrada(error):
    return render_template('404.html')

def pagina_no_encontrada(error):
    return redirect('login')

if __name__ == '__main__':
    csrf.init_app(app)
    app.register_error_handler(404, pagina_no_encontrada)
    app.register_error_handler(401, pagina_no_encontrada)
    app.run(debug=True, port=5000)