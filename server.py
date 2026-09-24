#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Cotizaciones y Control de Vehículos (ecotaler)
Servidor local con SQLite, solo stdlib (no requiere instalar nada).
Uso:   python server.py          -> sirve en http://localhost:8080
Abre con: http://localhost:8080
La base de datos se guarda automaticamente en cotizador.db
"""
import sqlite3, json, os, sys, webbrowser, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "cotizador.db")
HTML = os.path.join(BASE, "index.html")
PUERTO = int(os.environ.get("PORT", "8080"))
HOST = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
CLOUD = "PORT" in os.environ
NUM = lambda c, d=0: (c if c is not None else d)

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init():
    con = db(); cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS config(
        id INTEGER PRIMARY KEY CHECK(id=1),
        nombre TEXT DEFAULT 'ECOEXPRES', logo TEXT DEFAULT '🔧',
        dir TEXT DEFAULT '', tel TEXT DEFAULT '', mail TEXT DEFAULT '', nota TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS clientes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL, telefono TEXT DEFAULT '', email TEXT DEFAULT '',
        direccion TEXT DEFAULT '', fecha_registro TEXT DEFAULT (date('now'))
    );
    CREATE TABLE IF NOT EXISTS vehiculos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        marca TEXT DEFAULT '', modelo TEXT DEFAULT '', placa TEXT DEFAULT '',
        kilometraje TEXT DEFAULT '', observaciones TEXT DEFAULT '',
        fecha_ingreso TEXT DEFAULT (date('now')),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS productos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folio TEXT DEFAULT '', descripcion TEXT NOT NULL, categoria TEXT DEFAULT '', precio REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS cotizaciones(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folio INTEGER, vehiculo_id INTEGER NOT NULL, fecha TEXT DEFAULT (date('now')),
        nota TEXT DEFAULT '', total REAL DEFAULT 0,
        creada TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(vehiculo_id) REFERENCES vehiculos(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS cotizacion_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL, folio TEXT DEFAULT '', descripcion TEXT NOT NULL,
        cantidad INTEGER DEFAULT 1, precio REAL DEFAULT 0,
        FOREIGN KEY(cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE
    );
    """)
    # migracion: si la tabla ya existia sin las columnas nuevas, agregarlas
    for tabla_col in [('productos','folio'),('cotizacion_items','folio')]:
        try:
            cur.execute("ALTER TABLE {} ADD COLUMN {} TEXT DEFAULT ''".format(*tabla_col))
        except Exception:
            pass
    # config por defecto
    if cur.execute("SELECT COUNT(*) FROM config").fetchone()[0] == 0:
        cur.execute("INSERT INTO config(id,nombre,logo) VALUES(1,'ECOEXPRES','🔧')")
    con.commit(); con.close()

# ---------- helpers de lectura ----------
def filas(rows): 
    if hasattr(rows, 'fetchall'): rows = rows.fetchall()
    return [dict(r) for r in rows]

def veh_completo(row):
    d = dict(row)
    d['cliente_nombre'], d['cliente_tel'] = '', ''
    if row['cliente_id']:
        c = db().execute("SELECT nombre,telefono FROM clientes WHERE id=?", (row['cliente_id'],)).fetchone()
        if c: d['cliente_nombre'], d['cliente_tel'] = c['nombre'], c['telefono']
    return d

def cot_completo(row):
    d = dict(row)
    d['cliente_nombre'] = d['marca'] = d['modelo'] = d['placa'] = ''
    if row['vehiculo_id']:
        v = db().execute("SELECT v.*,c.nombre AS cn FROM vehiculos v LEFT JOIN clientes c ON c.id=v.cliente_id WHERE v.id=?", (row['vehiculo_id'],)).fetchone()
        if v:
            d['cliente_nombre'] = v['cn'] or ''
            d['marca'], d['modelo'], d['placa'] = v['marca'], v['modelo'], v['placa']
    return d

# ---------- logica ----------
def obtener_folio(cur, con):
    row = cur.execute("SELECT COALESCE(MAX(folio),0)+1 AS n FROM cotizaciones").fetchone()
    return row['n']

def crear_cotizacion(datos):
    con = db(); cur = con.cursor()
    vehid = NUM(datos.get('vehiculo_id'))
    if not vehid: return None, "Falta el vehículo"
    items = datos.get('items') or []
    folio = obtener_folio(cur, con)
    total = round(sum(NUM(i.get('cant'),1)*NUM(i.get('precio')) for i in items), 2)
    cur.execute("INSERT INTO cotizaciones(folio,vehiculo_id,fecha,nota,total) VALUES(?,?,?,?,?)",
                (folio, vehid, datos.get('fecha') or '', datos.get('nota') or '', total))
    cid = cur.lastrowid
    for it in items:
        cur.execute("INSERT INTO cotizacion_items(cotizacion_id,folio,descripcion,cantidad,precio) VALUES(?,?,?,?,?)",
                    (cid, it.get('folio') or '', it.get('desc'), NUM(it.get('cant'),1), NUM(it.get('precio'))))
    con.commit()
    cur.close(); con.close()
    # activo al dia el kilometraje si llego en la nota? no: se deja como esta.
    return {'id': cid, 'folio': folio, 'total': total}, None

class H(BaseHTTPRequestHandler):
    def _send(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def _leer(self):
        n = int(self.headers.get('Content-Length') or 0)
        if not n: return {}
        return json.loads(self.rfile.read(n).decode('utf-8'))
    def log_message(self, *a): pass

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path)
        p = ruta.path
        try:
            if p == '/' or p == '/index.html':
                try:
                    with open(HTML,'rb') as f: contenido=f.read()
                except FileNotFoundError:
                    contenido=b"<h1>No se encontro index.html</h1>"
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(contenido)))
                self.end_headers(); self.wfile.write(contenido); return

            elif p == '/api/vehiculos':
                con=db()
                rows=con.execute("SELECT * FROM vehiculos ORDER BY id DESC").fetchall()
                con.close()
                self._send({'data':[veh_completo(r) for r in rows]})

            elif p == '/api/vehiculos/' and False:
                pass
            elif p.startswith('/api/vehiculos/') and not p.endswith('/historial'):
                vid = p.split('/')[-1]
                con=db()
                v=con.execute("SELECT * FROM vehiculos WHERE id=?",(vid,)).fetchone()
                if not v: con.close(); self._send({'error':'no vehicle'},404); return
                hist=con.execute("SELECT id,folio,fecha,total,nota FROM cotizaciones WHERE vehiculo_id=? ORDER BY creada DESC",(vid,)).fetchall()
                con.close()
                veh=veh_completo(v)
                self._send({'vehiculo':veh,'historial':filas(hist)})

            elif p == '/api/clientes':
                con=db(); rows=con.execute("SELECT * FROM clientes ORDER BY nombre").fetchall(); con.close()
                self._send({'data':filas(rows)})

            elif p == '/api/productos':
                con=db(); rows=con.execute("SELECT * FROM productos ORDER BY descripcion").fetchall(); con.close()
                self._send({'data':filas(rows)})

            elif p == '/api/cotizaciones':
                con=db(); rows=con.execute("SELECT * FROM cotizaciones ORDER BY id DESC").fetchall(); con.close()
                self._send({'data':[cot_completo(r) for r in rows]})

            elif p.startswith('/api/cotizaciones/') and p != '/api/cotizaciones':
                cid=p.split('/')[-1]
                con=db()
                c=con.execute("SELECT * FROM cotizaciones WHERE id=?",(cid,)).fetchone()
                if not c: con.close(); self._send({'error':'no'},404); return
                its=con.execute("SELECT * FROM cotizacion_items WHERE cotizacion_id=?",(cid,)).fetchall()
                v=con.execute("SELECT * FROM vehiculos WHERE id=?",(c['vehiculo_id'],)).fetchone()
                con.close()
                self._send({'cotizacion':dict(c),'items':filas(its),
                            'vehiculo': veh_completo(v) if v else None})

            elif p == '/api/config':
                con=db(); c=con.execute("SELECT * FROM config WHERE id=1").fetchone() or {}
                con.close()
                self._send(dict(c))

            elif p == '/api/respaldo':
                con=db()
                data={'config':filas(con.execute("SELECT * FROM config").fetchall()),
                      'clientes':filas(con.execute("SELECT * FROM clientes").fetchall()),
                      'vehiculos':filas(con.execute("SELECT * FROM vehiculos").fetchall()),
                      'productos':filas(con.execute("SELECT * FROM productos").fetchall()),
                      'cotizaciones':filas(con.execute("SELECT * FROM cotizaciones").fetchall()),
                      'cotizacion_items':filas(con.execute("SELECT * FROM cotizacion_items").fetchall())}
                con.close()
                self._send(data)
            else:
                self._send({'error':'not found'},404)
        except Exception as e:
            self._send({'error':str(e)},500)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        d = self._leer()
        try:
            if p == '/api/vehiculos':
                con=db(); cur=con.cursor()
                cliente_id = NUM(d.get('cliente_id'))
                # si viene cliente nuevo, crearlo
                nombre_nuevo=(d.get('cliente_nombre') or '').strip()
                if nombre_nuevo and not cliente_id:
                    cur.execute("INSERT INTO clientes(nombre,telefono) VALUES(?,?)",
                                (nombre_nuevo, d.get('cliente_tel') or ''))
                    cliente_id=cur.lastrowid
                elif not cliente_id:
                    con.close(); self._send({'error':'cliente requerido'},400); return
                cur.execute("""INSERT INTO vehiculos(cliente_id,marca,modelo,placa,kilometraje,observaciones,fecha_ingreso)
                               VALUES(?,?,?,?,?,?,?)""",
                            (cliente_id, d.get('marca'),d.get('modelo'),d.get('placa'),
                             d.get('kilometraje'), d.get('observaciones'), d.get('fecha_ingreso') or ''))
                vid=cur.lastrowid; con.commit(); con.close()
                self._send({'id':vid})

            elif p == '/api/vehiculos/<id>':
                pass

            elif p == '/api/clientes':
                con=db(); cur=con.cursor()
                cur.execute("INSERT INTO clientes(nombre,telefono,email,direccion) VALUES(?,?,?,?)",
                            (d.get('nombre'),d.get('telefono'),d.get('email'),d.get('direccion')))
                cid=cur.lastrowid; con.commit(); con.close()
                self._send({'id':cid})

            elif p == '/api/productos':
                con=db(); cur=con.cursor()
                cur.execute("INSERT INTO productos(folio,descripcion,categoria,precio) VALUES(?,?,?,?)",
                            (d.get('folio') or '',d.get('descripcion'),d.get('categoria'),NUM(d.get('precio'))))
                pid=cur.lastrowid; con.commit(); con.close()
                self._send({'id':pid})

            elif p == '/api/cotizaciones':
                res,err=crear_cotizacion(d)
                if err: self._send({'error':err},400)
                else: self._send(res)

            elif p == '/api/config':
                con=db(); cur=con.cursor()
                cur.execute("""UPDATE config SET nombre=?,logo=?,dir=?,tel=?,mail=?,nota=? WHERE id=1""",
                            (d.get('nombre'),d.get('logo'),d.get('dir'),d.get('tel'),d.get('mail'),d.get('nota')))
                if cur.rowcount==0:
                    cur.execute("INSERT INTO config(id,nombre,logo,dir,tel,mail,nota) VALUES(1,?,?,?,?,?,?)",
                                (d.get('nombre'),d.get('logo'),d.get('dir'),d.get('tel'),d.get('mail'),d.get('nota')))
                con.commit(); con.close(); self._send({'ok':True})

            elif p == '/api/restaurar':
                con=db(); cur=con.cursor()
                # vaciar
                for t in ['cotizacion_items','cotizaciones','productos','vehiculos','clientes','config']:
                    cur.execute("DELETE FROM {}".format(t))
                import itertools
                for cfg in d.get('config',[]):
                    cur.execute("INSERT INTO config(id,nombre,logo,dir,tel,mail,nota) VALUES(1,?,?,?,?,?,?)",
                                (cfg.get('nombre'),cfg.get('logo'),cfg.get('dir'),cfg.get('tel'),cfg.get('mail'),cfg.get('nota')))
                for c in d.get('clientes',[]):
                    cur.execute("INSERT INTO clientes(id,nombre,telefono,email,direccion,fecha_registro) VALUES(?,?,?,?,?,?)",
                                (c['id'],c.get('nombre'),c.get('telefono'),c.get('email'),c.get('direccion'),c.get('fecha_registro')))
                for v in d.get('vehiculos',[]):
                    cur.execute("INSERT INTO vehiculos(id,cliente_id,marca,modelo,placa,kilometraje,observaciones,fecha_ingreso) VALUES(?,?,?,?,?,?,?,?)",
                                (v['id'],v.get('cliente_id'),v.get('marca'),v.get('modelo'),v.get('placa'),v.get('kilometraje'),v.get('observaciones'),v.get('fecha_ingreso')))
                for p_ in d.get('productos',[]):
                    cur.execute("INSERT INTO productos(id,folio,descripcion,categoria,precio) VALUES(?,?,?,?,?)",
                                (p_['id'],p_.get('folio') or '',p_.get('descripcion'),p_.get('categoria'),p_.get('precio')))
                for c in d.get('cotizaciones',[]):
                    cur.execute("INSERT INTO cotizaciones(id,folio,vehiculo_id,fecha,nota,total,creada) VALUES(?,?,?,?,?,?,?)",
                                (c['id'],c.get('folio'),c.get('vehiculo_id'),c.get('fecha'),c.get('nota'),c.get('total'),c.get('creada')))
                for i_ in d.get('cotizacion_items',[]):
                    cur.execute("INSERT INTO cotizacion_items(id,cotizacion_id,folio,descripcion,cantidad,precio) VALUES(?,?,?,?,?,?)",
                                (i_['id'],i_['cotizacion_id'],i_.get('folio') or '',i_.get('descripcion'),i_.get('cantidad'),i_.get('precio')))
                con.commit(); con.close(); self._send({'ok':True})
            else:
                self._send({'error':'not found'},404)
        except Exception as e:
            self._send({'error':str(e)},500)

    def do_DELETE(self):
        p = urllib.parse.urlparse(self.path).path
        try:
            con=db(); cur=con.cursor()
            if p.startswith('/api/vehiculos/'):
                vid=p.split('/')[-1]
                cur.execute("DELETE FROM vehiculos WHERE id=?",(vid,))
            elif p.startswith('/api/clientes/'):
                cid=p.split('/')[-1]
                cur.execute("DELETE FROM clientes WHERE id=?",(cid,))
            elif p.startswith('/api/cotizaciones/'):
                cod=p.split('/')[-1]
                cur.execute("DELETE FROM cotizaciones WHERE id=?",(cod,))
            elif p.startswith('/api/productos/'):
                pid=p.split('/')[-1]
                cur.execute("DELETE FROM productos WHERE id=?",(pid,))
            else:
                con.close(); self._send({'error':'not found'},404); return
            con.commit(); con.close(); self._send({'ok':True})
        except Exception as e:
            self._send({'error':str(e)},500)

def main():
    init()
    try:
        srv = ThreadingHTTPServer((HOST, PUERTO), H)
    except OSError:
        print("El puerto {} esta ocupado. ;asegurate que no este abierto ya el programa o revisa otro proceso.".format(PUERTO))
        sys.exit(1)
    print("="*52)
    print("  SISTEMA DE COTIZACIONES Y CONTROL DE VEHICULOS")
    print("  Base de datos: cotizador.db")
    print("  Servidor:     http://localhost:{0}".format(PUERTO))
    print("  Detén con:    Ctrl + C")
    print("="*52)
    if not CLOUD:
        threading.Timer(0.8, lambda: webbrowser.open("http://localhost:{0}".format(PUERTO))).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando…")
        srv.shutdown()

if __name__ == '__main__':
    main()
