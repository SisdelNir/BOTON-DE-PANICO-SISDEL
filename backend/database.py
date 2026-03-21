"""
Botón de Pánico SISDEL — Base de Datos
Soporta PostgreSQL (Render) y SQLite (local)
"""

import uuid, random, string, os, json
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

CLAVE_PROGRAMADOR = "1122"
NOMBRE_SISTEMA    = "Botón de Pánico SISDEL"

# ── Detectar motor ──────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_PG = DATABASE_URL.startswith("postgresql")

if USE_PG:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3
    _DATA_DIR = "/data" if os.path.isdir("/data") else os.path.dirname(__file__)
    DB_PATH = os.path.join(_DATA_DIR, "sisdel.db")


def generar_clave_6(nombre: str = None) -> str:
    letras = [c for c in (nombre or '').upper() if c.isalpha()]
    if letras and len(letras) >= 2:
        l1, l3 = letras[0], letras[-1]
    else:
        l1 = random.choice(string.ascii_uppercase)
        l3 = random.choice(string.ascii_uppercase)
    l2   = random.choice(string.ascii_uppercase)
    nums = ''.join(random.choices(string.digits, k=3))
    return f"{l1}{l2}{l3}{nums}"


# ── Parámetro placeholder ──────────────────────────────────
# PostgreSQL usa %s, SQLite usa ?
PH = "%s" if USE_PG else "?"


def _ph(sql_with_qmark: str) -> str:
    """Convierte SQL con ? placeholders a %s si es PostgreSQL."""
    if USE_PG:
        return sql_with_qmark.replace("?", "%s")
    return sql_with_qmark


@contextmanager
def get_conn():
    if USE_PG:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _fetchone(conn, sql, params=()):
    """Ejecuta y retorna una fila como dict."""
    if USE_PG:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    else:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def _fetchall(conn, sql, params=()):
    """Ejecuta y retorna todas las filas como list[dict]."""
    if USE_PG:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    else:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def _execute(conn, sql, params=()):
    """Ejecuta SQL y retorna el cursor."""
    if USE_PG:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    else:
        return conn.execute(sql, params)


# ── Init DB ─────────────────────────────────────────────────

def init_db():
    """Crea las tablas si no existen."""
    with get_conn() as conn:
        if USE_PG:
            _execute(conn, """
            CREATE TABLE IF NOT EXISTS instituciones (
                id_institucion    TEXT PRIMARY KEY,
                nombre_institucion TEXT NOT NULL,
                nombre_admin      TEXT NOT NULL,
                telefono          TEXT DEFAULT '',
                correo            TEXT DEFAULT '',
                direccion         TEXT DEFAULT '',
                clave_acceso      TEXT NOT NULL,
                activo            BOOLEAN DEFAULT TRUE,
                fecha_registro    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claves_vecinos (
                id_clave        SERIAL PRIMARY KEY,
                clave           TEXT NOT NULL,
                id_institucion  TEXT NOT NULL REFERENCES instituciones(id_institucion),
                descripcion     TEXT DEFAULT '',
                usada           BOOLEAN DEFAULT FALSE,
                id_vecino       TEXT,
                fecha_creacion  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vecinos (
                id_vecino          TEXT PRIMARY KEY,
                id_institucion     TEXT NOT NULL REFERENCES instituciones(id_institucion),
                nombre             TEXT NOT NULL,
                telefono           TEXT NOT NULL,
                num_identificacion TEXT NOT NULL,
                direccion          TEXT DEFAULT '',
                sexo               TEXT DEFAULT '',
                edad               INTEGER DEFAULT 0,
                correo             TEXT DEFAULT '',
                codigo_vecino      TEXT DEFAULT '',
                clave_acceso       TEXT DEFAULT '',
                activo             BOOLEAN DEFAULT TRUE,
                fecha_registro     TEXT NOT NULL,
                UNIQUE (id_institucion, num_identificacion)
            );

            CREATE TABLE IF NOT EXISTS emergencias (
                id_emergencia        TEXT PRIMARY KEY,
                id_institucion       TEXT NOT NULL REFERENCES instituciones(id_institucion),
                id_vecino            TEXT,
                nombre_vecino        TEXT DEFAULT 'Desconocido',
                telefono_vecino      TEXT DEFAULT '',
                num_identificacion   TEXT DEFAULT '',
                direccion_vecino     TEXT DEFAULT '',
                gps_latitud          REAL,
                gps_longitud         REAL,
                direccion_aproximada TEXT DEFAULT '',
                estatus              TEXT DEFAULT 'ACTIVA',
                notas_operador       TEXT,
                fecha_creacion       TEXT NOT NULL,
                fecha_atencion       TEXT
            );
            """)
        else:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS instituciones (
                id_institucion    TEXT PRIMARY KEY,
                nombre_institucion TEXT NOT NULL,
                nombre_admin      TEXT NOT NULL,
                telefono          TEXT DEFAULT '',
                correo            TEXT DEFAULT '',
                direccion         TEXT DEFAULT '',
                clave_acceso      TEXT NOT NULL,
                activo            INTEGER DEFAULT 1,
                fecha_registro    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claves_vecinos (
                id_clave        INTEGER PRIMARY KEY AUTOINCREMENT,
                clave           TEXT NOT NULL,
                id_institucion  TEXT NOT NULL,
                descripcion     TEXT DEFAULT '',
                usada           INTEGER DEFAULT 0,
                id_vecino       TEXT,
                fecha_creacion  TEXT NOT NULL,
                FOREIGN KEY (id_institucion) REFERENCES instituciones(id_institucion)
            );

            CREATE TABLE IF NOT EXISTS vecinos (
                id_vecino          TEXT PRIMARY KEY,
                id_institucion     TEXT NOT NULL,
                nombre             TEXT NOT NULL,
                telefono           TEXT NOT NULL,
                num_identificacion TEXT NOT NULL,
                direccion          TEXT DEFAULT '',
                sexo               TEXT DEFAULT '',
                edad               INTEGER DEFAULT 0,
                correo             TEXT DEFAULT '',
                codigo_vecino      TEXT DEFAULT '',
                clave_acceso       TEXT DEFAULT '',
                activo             INTEGER DEFAULT 1,
                fecha_registro     TEXT NOT NULL,
                FOREIGN KEY (id_institucion) REFERENCES instituciones(id_institucion),
                UNIQUE (id_institucion, num_identificacion)
            );

            CREATE TABLE IF NOT EXISTS emergencias (
                id_emergencia        TEXT PRIMARY KEY,
                id_institucion       TEXT NOT NULL,
                id_vecino            TEXT,
                nombre_vecino        TEXT DEFAULT 'Desconocido',
                telefono_vecino      TEXT DEFAULT '',
                num_identificacion   TEXT DEFAULT '',
                direccion_vecino     TEXT DEFAULT '',
                gps_latitud          REAL,
                gps_longitud         REAL,
                direccion_aproximada TEXT DEFAULT '',
                estatus              TEXT DEFAULT 'ACTIVA',
                notas_operador       TEXT,
                fecha_creacion       TEXT NOT NULL,
                fecha_atencion       TEXT,
                FOREIGN KEY (id_institucion) REFERENCES instituciones(id_institucion)
            );
            """)

        # Demo seed
        count = _fetchone(conn, "SELECT COUNT(*) as cnt FROM instituciones")
        if count and count["cnt"] == 0:
            _seed_demo(conn)

    # Restaurar instituciones desde env var
    _seed_from_env()


def _seed_demo(conn):
    inst_id = str(uuid.uuid4())
    clave   = generar_clave_6("Colonia Demo")
    now     = datetime.now().isoformat()
    _execute(conn, _ph("""
        INSERT INTO instituciones
        (id_institucion, nombre_institucion, nombre_admin, telefono, correo, direccion, clave_acceso, activo, fecha_registro)
        VALUES (?,?,?,?,?,?,?,?,?)
    """), (inst_id, "Colonia Demo", "Admin Demo", "5550000000", "demo@sisdel.mx", "Calle Principal #1", clave, True if USE_PG else 1, now))


def _seed_from_env():
    raw = os.environ.get("SEED_INSTITUCIONES", "")
    if not raw:
        return
    try:
        items = json.loads(raw)
    except Exception:
        return

    now = datetime.now().isoformat()
    with get_conn() as conn:
        for item in items:
            nombre = item.get("nombre", "")
            clave  = item.get("clave") or generar_clave_6(nombre)
            exists = _fetchone(conn, _ph(
                "SELECT 1 FROM instituciones WHERE nombre_institucion=?"
            ), (nombre,))
            if not exists:
                _execute(conn, _ph("""
                    INSERT INTO instituciones
                    (id_institucion,nombre_institucion,nombre_admin,telefono,correo,direccion,clave_acceso,activo,fecha_registro)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """), (str(uuid.uuid4()), nombre,
                       item.get("admin","Admin"),
                       item.get("tel",""),
                       item.get("correo",""),
                       item.get("dir",""),
                       clave, True if USE_PG else 1, now))


class Database:
    """Interfaz de acceso a datos — PostgreSQL o SQLite."""

    # ── INSTITUCIONES ────────────────────────────────────────

    def crear_institucion(self, data: dict) -> dict:
        inst = {
            "id_institucion":    str(uuid.uuid4()),
            "nombre_institucion": data["nombre_institucion"],
            "nombre_admin":       data["nombre_admin"],
            "telefono":           data.get("telefono", ""),
            "correo":             data.get("correo", ""),
            "direccion":          data.get("direccion", ""),
            "clave_acceso":       generar_clave_6(data["nombre_institucion"]),
            "activo":             True,
            "fecha_registro":     datetime.now().isoformat(),
        }
        with get_conn() as conn:
            _execute(conn, _ph("""
                INSERT INTO instituciones
                (id_institucion, nombre_institucion, nombre_admin, telefono, correo, direccion, clave_acceso, activo, fecha_registro)
                VALUES (?,?,?,?,?,?,?,?,?)
            """), (inst["id_institucion"], inst["nombre_institucion"], inst["nombre_admin"],
                   inst["telefono"], inst["correo"], inst["direccion"], inst["clave_acceso"],
                   True if USE_PG else 1, inst["fecha_registro"]))
        return inst

    def listar_instituciones(self) -> List[dict]:
        with get_conn() as conn:
            rows = _fetchall(conn, "SELECT * FROM instituciones ORDER BY fecha_registro")
        return [r | {"activo": bool(r["activo"])} for r in rows]

    def obtener_institucion(self, id_inst: str) -> Optional[dict]:
        with get_conn() as conn:
            row = _fetchone(conn, _ph("SELECT * FROM instituciones WHERE id_institucion=?"), (id_inst,))
        if not row: return None
        return row | {"activo": bool(row["activo"])}

    def obtener_institucion_por_clave(self, clave: str) -> Optional[dict]:
        with get_conn() as conn:
            row = _fetchone(conn, _ph(
                "SELECT * FROM instituciones WHERE UPPER(clave_acceso)=UPPER(?) AND activo=?"
            ), (clave, True if USE_PG else 1))
        if not row: return None
        return row | {"activo": True}

    def toggle_institucion(self, id_inst: str) -> Optional[dict]:
        with get_conn() as conn:
            if USE_PG:
                _execute(conn, "UPDATE instituciones SET activo = NOT activo WHERE id_institucion=%s", (id_inst,))
            else:
                _execute(conn, "UPDATE instituciones SET activo = CASE WHEN activo=1 THEN 0 ELSE 1 END WHERE id_institucion=?", (id_inst,))
            row = _fetchone(conn, _ph("SELECT * FROM instituciones WHERE id_institucion=?"), (id_inst,))
        if not row: return None
        return row | {"activo": bool(row["activo"])}

    def regenerar_clave_institucion(self, id_inst: str) -> Optional[dict]:
        row = self.obtener_institucion(id_inst)
        if not row: return None
        nueva = generar_clave_6(row["nombre_institucion"])
        with get_conn() as conn:
            _execute(conn, _ph("UPDATE instituciones SET clave_acceso=? WHERE id_institucion=?"), (nueva, id_inst))
        row["clave_acceso"] = nueva
        return row

    def editar_institucion(self, id_inst: str, campos: dict) -> Optional[dict]:
        row = self.obtener_institucion(id_inst)
        if not row: return None
        allowed = {"nombre_institucion","nombre_admin","telefono","correo","direccion"}
        sets, vals = [], []
        for k, v in campos.items():
            if k in allowed and v is not None:
                sets.append(f"{k}={PH}")
                vals.append(v)
        if not sets: return row
        vals.append(id_inst)
        with get_conn() as conn:
            _execute(conn, f"UPDATE instituciones SET {', '.join(sets)} WHERE id_institucion={PH}", vals)
        return self.obtener_institucion(id_inst)

    def eliminar_institucion(self, id_inst: str) -> bool:
        with get_conn() as conn:
            cur = _execute(conn, _ph("DELETE FROM instituciones WHERE id_institucion=?"), (id_inst,))
        return cur.rowcount > 0

    # ── CLAVES VECINOS ───────────────────────────────────────

    def generar_clave_vecino(self, id_institucion: str, descripcion: str = "") -> dict:
        clave_data = {
            "clave":          generar_clave_6(),
            "id_institucion": id_institucion,
            "descripcion":    descripcion,
            "usada":          False,
            "id_vecino":      None,
            "fecha_creacion": datetime.now().isoformat(),
        }
        with get_conn() as conn:
            if USE_PG:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO claves_vecinos (clave, id_institucion, descripcion, usada, id_vecino, fecha_creacion)
                    VALUES (%s,%s,%s,FALSE,NULL,%s) RETURNING id_clave
                """, (clave_data["clave"], clave_data["id_institucion"], clave_data["descripcion"], clave_data["fecha_creacion"]))
                clave_data["id_clave"] = cur.fetchone()[0]
                cur.close()
            else:
                cur = conn.execute("""
                    INSERT INTO claves_vecinos (clave, id_institucion, descripcion, usada, id_vecino, fecha_creacion)
                    VALUES (?,?,?,0,NULL,?)
                """, (clave_data["clave"], clave_data["id_institucion"], clave_data["descripcion"], clave_data["fecha_creacion"]))
                clave_data["id_clave"] = cur.lastrowid
        return clave_data

    def validar_clave_vecino(self, clave: str, id_institucion: str = None) -> Optional[dict]:
        sql = _ph("SELECT * FROM claves_vecinos WHERE UPPER(clave)=UPPER(?)")
        params = [clave]
        if id_institucion:
            sql += f" AND id_institucion={PH}"
            params.append(id_institucion)
        with get_conn() as conn:
            row = _fetchone(conn, sql, params)
        if not row: return None
        return row | {"usada": bool(row["usada"])}

    def listar_claves_vecinos(self, id_institucion: str) -> List[dict]:
        with get_conn() as conn:
            rows = _fetchall(conn, _ph("SELECT * FROM claves_vecinos WHERE id_institucion=? ORDER BY id_clave"), (id_institucion,))
        return [r | {"usada": bool(r["usada"])} for r in rows]

    def eliminar_clave_vecino(self, id_clave: int) -> bool:
        with get_conn() as conn:
            cur = _execute(conn, _ph("DELETE FROM claves_vecinos WHERE id_clave=?"), (id_clave,))
        return cur.rowcount > 0

    # ── VECINOS ──────────────────────────────────────────────

    def registrar_vecino(self, data: dict) -> dict:
        existente = self.buscar_vecino_por_identificacion(data["num_identificacion"], data["id_institucion"])
        if existente:
            campos_editar = {k: data[k] for k in ("nombre","telefono","direccion","sexo","edad","correo") if k in data}
            sets = [f"{k}={PH}" for k in campos_editar]
            vals = list(campos_editar.values()) + [existente["id_vecino"]]
            if sets:
                with get_conn() as conn:
                    _execute(conn, f"UPDATE vecinos SET {', '.join(sets)} WHERE id_vecino={PH}", vals)
            return self.buscar_vecino_por_identificacion(data["num_identificacion"], data["id_institucion"])

        vecino = {
            "id_vecino":          str(uuid.uuid4()),
            "id_institucion":     data["id_institucion"],
            "nombre":             data["nombre"],
            "telefono":           data["telefono"],
            "num_identificacion": data["num_identificacion"],
            "direccion":          data.get("direccion", ""),
            "sexo":               data.get("sexo", ""),
            "edad":               data.get("edad", 0),
            "correo":             data.get("correo", ""),
            "codigo_vecino":      generar_clave_6(data["nombre"]),
            "clave_acceso":       data.get("clave_acceso", ""),
            "activo":             True,
            "fecha_registro":     datetime.now().isoformat(),
        }
        with get_conn() as conn:
            _execute(conn, _ph("""
                INSERT INTO vecinos
                (id_vecino,id_institucion,nombre,telefono,num_identificacion,direccion,sexo,edad,correo,codigo_vecino,clave_acceso,activo,fecha_registro)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """), (vecino["id_vecino"], vecino["id_institucion"], vecino["nombre"], vecino["telefono"],
                   vecino["num_identificacion"], vecino["direccion"], vecino["sexo"], vecino["edad"],
                   vecino["correo"], vecino["codigo_vecino"], vecino["clave_acceso"],
                   True if USE_PG else 1, vecino["fecha_registro"]))
            if data.get("clave_acceso"):
                _execute(conn, _ph(
                    "UPDATE claves_vecinos SET usada=?, id_vecino=? WHERE UPPER(clave)=UPPER(?)"
                ), (True if USE_PG else 1, vecino["id_vecino"], data["clave_acceso"]))
        return vecino

    def buscar_vecino_por_identificacion(self, num_id: str, id_institucion: str) -> Optional[dict]:
        with get_conn() as conn:
            row = _fetchone(conn, _ph(
                "SELECT * FROM vecinos WHERE id_institucion=? AND UPPER(num_identificacion)=UPPER(?)"
            ), (id_institucion, num_id))
        if not row: return None
        return row | {"activo": bool(row["activo"])}

    def obtener_vecino_por_clave(self, clave: str) -> Optional[dict]:
        with get_conn() as conn:
            row = _fetchone(conn, _ph("SELECT * FROM vecinos WHERE UPPER(clave_acceso)=UPPER(?)"), (clave,))
        if not row: return None
        return row | {"activo": bool(row["activo"])}

    @property
    def vecinos(self):
        with get_conn() as conn:
            rows = _fetchall(conn, "SELECT * FROM vecinos")
        return {r["id_vecino"]: r | {"activo": bool(r["activo"])} for r in rows}

    def listar_vecinos(self, id_institucion: str) -> List[dict]:
        with get_conn() as conn:
            rows = _fetchall(conn, _ph("SELECT * FROM vecinos WHERE id_institucion=? ORDER BY fecha_registro"), (id_institucion,))
        return [r | {"activo": bool(r["activo"])} for r in rows]

    def eliminar_vecino(self, id_vecino: str) -> bool:
        with get_conn() as conn:
            cur = _execute(conn, _ph("DELETE FROM vecinos WHERE id_vecino=?"), (id_vecino,))
        return cur.rowcount > 0

    def actualizar_vecino(self, id_vecino: str, data: dict) -> Optional[dict]:
        campos = ["nombre","telefono","direccion","sexo","edad","correo"]
        sets   = [f"{c}={PH}" for c in campos if c in data]
        vals   = [data[c] for c in campos if c in data]
        if not sets: return None
        vals.append(id_vecino)
        with get_conn() as conn:
            _execute(conn, f"UPDATE vecinos SET {', '.join(sets)} WHERE id_vecino={PH}", vals)
            row = _fetchone(conn, _ph("SELECT * FROM vecinos WHERE id_vecino=?"), (id_vecino,))
        return row | {"activo": bool(row["activo"])} if row else None

    # ── EMERGENCIAS ──────────────────────────────────────────

    def crear_emergencia(self, data: dict) -> dict:
        e = {
            "id_emergencia":        str(uuid.uuid4()),
            "id_institucion":       data["id_institucion"],
            "id_vecino":            data.get("id_vecino"),
            "nombre_vecino":        data.get("nombre_vecino","Desconocido"),
            "telefono_vecino":      data.get("telefono_vecino",""),
            "num_identificacion":   data.get("num_identificacion",""),
            "direccion_vecino":     data.get("direccion_vecino",""),
            "gps_latitud":          data.get("gps_latitud"),
            "gps_longitud":         data.get("gps_longitud"),
            "direccion_aproximada": data.get("direccion_aproximada",""),
            "estatus":              "ACTIVA",
            "notas_operador":       None,
            "fecha_creacion":       datetime.now().isoformat(),
            "fecha_atencion":       None,
        }
        with get_conn() as conn:
            _execute(conn, _ph("""
                INSERT INTO emergencias
                (id_emergencia,id_institucion,id_vecino,nombre_vecino,telefono_vecino,num_identificacion,
                 direccion_vecino,gps_latitud,gps_longitud,direccion_aproximada,estatus,notas_operador,fecha_creacion,fecha_atencion)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """), (e["id_emergencia"], e["id_institucion"], e["id_vecino"], e["nombre_vecino"],
                   e["telefono_vecino"], e["num_identificacion"], e["direccion_vecino"],
                   e["gps_latitud"], e["gps_longitud"], e["direccion_aproximada"],
                   e["estatus"], e["notas_operador"], e["fecha_creacion"], e["fecha_atencion"]))
        return e

    def listar_emergencias(self, id_institucion: str, estatus: str = None) -> List[dict]:
        sql = _ph("SELECT * FROM emergencias WHERE id_institucion=?")
        params = [id_institucion]
        if estatus:
            sql += f" AND estatus={PH}"
            params.append(estatus)
        sql += " ORDER BY fecha_creacion DESC"
        with get_conn() as conn:
            rows = _fetchall(conn, sql, params)
        return rows

    def actualizar_estatus_emergencia(self, id_emergencia: str, estatus: str, notas: str = None) -> Optional[dict]:
        fecha_atencion = datetime.now().isoformat() if estatus in ("ATENDIDA","FALSA_ALARMA","CANCELADA") else None
        with get_conn() as conn:
            _execute(conn, _ph("""
                UPDATE emergencias SET estatus=?, notas_operador=COALESCE(?,notas_operador), fecha_atencion=COALESCE(?,fecha_atencion)
                WHERE id_emergencia=?
            """), (estatus, notas, fecha_atencion, id_emergencia))
            row = _fetchone(conn, _ph("SELECT * FROM emergencias WHERE id_emergencia=?"), (id_emergencia,))
        return row

    def stats_institucion(self, id_institucion: str) -> dict:
        with get_conn() as conn:
            total   = _fetchone(conn, _ph("SELECT COUNT(*) as cnt FROM emergencias WHERE id_institucion=?"), (id_institucion,))["cnt"]
            activas = _fetchone(conn, _ph("SELECT COUNT(*) as cnt FROM emergencias WHERE id_institucion=? AND estatus='ACTIVA'"), (id_institucion,))["cnt"]
            camino  = _fetchone(conn, _ph("SELECT COUNT(*) as cnt FROM emergencias WHERE id_institucion=? AND estatus='EN_CAMINO'"), (id_institucion,))["cnt"]
            atend   = _fetchone(conn, _ph("SELECT COUNT(*) as cnt FROM emergencias WHERE id_institucion=? AND estatus='ATENDIDA'"), (id_institucion,))["cnt"]
            vecinos = _fetchone(conn, _ph("SELECT COUNT(*) as cnt FROM vecinos WHERE id_institucion=?"), (id_institucion,))["cnt"]
        return {"total": total, "activas": activas, "en_camino": camino, "atendidas": atend, "vecinos_registrados": vecinos}


# Inicializar tablas y objeto global
init_db()
db = Database()
