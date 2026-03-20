"""
Botón de Pánico SISDEL — Base de Datos SQLite Persistente
Tablas: instituciones, claves_vecinos, vecinos, emergencias
"""

import uuid, random, string, sqlite3, os
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import contextmanager

CLAVE_PROGRAMADOR = "1122"
NOMBRE_SISTEMA    = "Botón de Pánico SISDEL"

# Ruta del archivo SQLite (junto al backend)
DB_PATH = os.path.join(os.path.dirname(__file__), "sisdel.db")


def generar_clave_6(nombre: str = None) -> str:
    """
    Clave de 6 chars:
      L1 = primera letra del nombre
      L2 = letra al azar
      L3 = última letra del nombre
      N1 N2 N3 = dígitos al azar
    """
    letras = [c for c in (nombre or '').upper() if c.isalpha()]
    if letras and len(letras) >= 2:
        l1 = letras[0]
        l3 = letras[-1]
    else:
        l1 = random.choice(string.ascii_uppercase)
        l3 = random.choice(string.ascii_uppercase)
    l2   = random.choice(string.ascii_uppercase)
    nums = ''.join(random.choices(string.digits, k=3))
    return f"{l1}{l2}{l3}{nums}"


def _row_to_dict(row) -> dict:
    """Convierte sqlite3.Row a dict."""
    return dict(row) if row else None


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # mejor concurrencia
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crea las tablas si no existen."""
    with get_conn() as conn:
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

        # Insertar institución demo solo si la tabla está vacía
        cur = conn.execute("SELECT COUNT(*) FROM instituciones")
        if cur.fetchone()[0] == 0:
            _seed_demo(conn)


def _seed_demo(conn):
    """Institución demo inicial."""
    inst_id = str(uuid.uuid4())
    clave   = generar_clave_6("Colonia Demo")
    now     = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO instituciones
        (id_institucion, nombre_institucion, nombre_admin, telefono, correo, direccion, clave_acceso, activo, fecha_registro)
        VALUES (?,?,?,?,?,?,?,1,?)
    """, (inst_id, "Colonia Demo", "Admin Demo", "5550000000", "demo@sisdel.mx", "Calle Principal #1", clave, now))


class Database:
    """Interfaz de acceso a datos — SQLite persistente."""

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
            conn.execute("""
                INSERT INTO instituciones
                (id_institucion, nombre_institucion, nombre_admin, telefono, correo, direccion, clave_acceso, activo, fecha_registro)
                VALUES (:id_institucion,:nombre_institucion,:nombre_admin,:telefono,:correo,:direccion,:clave_acceso,1,:fecha_registro)
            """, inst)
        return inst

    def listar_instituciones(self) -> List[dict]:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM instituciones ORDER BY fecha_registro").fetchall()
        return [dict(r) | {"activo": bool(r["activo"])} for r in rows]

    def obtener_institucion(self, id_inst: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM instituciones WHERE id_institucion=?", (id_inst,)).fetchone()
        if not row: return None
        return dict(row) | {"activo": bool(row["activo"])}

    def obtener_institucion_por_clave(self, clave: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM instituciones WHERE UPPER(clave_acceso)=UPPER(?) AND activo=1",
                (clave,)
            ).fetchone()
        if not row: return None
        return dict(row) | {"activo": True}

    def toggle_institucion(self, id_inst: str) -> Optional[dict]:
        with get_conn() as conn:
            conn.execute(
                "UPDATE instituciones SET activo = CASE WHEN activo=1 THEN 0 ELSE 1 END WHERE id_institucion=?",
                (id_inst,)
            )
            row = conn.execute("SELECT * FROM instituciones WHERE id_institucion=?", (id_inst,)).fetchone()
        if not row: return None
        return dict(row) | {"activo": bool(row["activo"])}

    def regenerar_clave_institucion(self, id_inst: str) -> Optional[dict]:
        row = self.obtener_institucion(id_inst)
        if not row: return None
        nueva = generar_clave_6(row["nombre_institucion"])
        with get_conn() as conn:
            conn.execute("UPDATE instituciones SET clave_acceso=? WHERE id_institucion=?", (nueva, id_inst))
        row["clave_acceso"] = nueva
        return row

    def editar_institucion(self, id_inst: str, campos: dict) -> Optional[dict]:
        row = self.obtener_institucion(id_inst)
        if not row: return None
        allowed = {"nombre_institucion","nombre_admin","telefono","correo","direccion"}
        sets, vals = [], []
        for k, v in campos.items():
            if k in allowed and v is not None:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets: return row
        vals.append(id_inst)
        with get_conn() as conn:
            conn.execute(f"UPDATE instituciones SET {', '.join(sets)} WHERE id_institucion=?", vals)
        return self.obtener_institucion(id_inst)

    def eliminar_institucion(self, id_inst: str) -> bool:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM instituciones WHERE id_institucion=?", (id_inst,))
        return cur.rowcount > 0

    # ── CLAVES VECINOS ───────────────────────────────────────

    def generar_clave_vecino(self, id_institucion: str, descripcion: str = "") -> dict:
        clave = {
            "clave":          generar_clave_6(),
            "id_institucion": id_institucion,
            "descripcion":    descripcion,
            "usada":          False,
            "id_vecino":      None,
            "fecha_creacion": datetime.now().isoformat(),
        }
        with get_conn() as conn:
            cur = conn.execute("""
                INSERT INTO claves_vecinos (clave, id_institucion, descripcion, usada, id_vecino, fecha_creacion)
                VALUES (:clave,:id_institucion,:descripcion,0,NULL,:fecha_creacion)
            """, clave)
            clave["id_clave"] = cur.lastrowid
        return clave

    def validar_clave_vecino(self, clave: str, id_institucion: str = None) -> Optional[dict]:
        sql = "SELECT * FROM claves_vecinos WHERE UPPER(clave)=UPPER(?)"
        params: list = [clave]
        if id_institucion:
            sql += " AND id_institucion=?"
            params.append(id_institucion)
        with get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
        if not row: return None
        return dict(row) | {"usada": bool(row["usada"])}

    def listar_claves_vecinos(self, id_institucion: str) -> List[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM claves_vecinos WHERE id_institucion=? ORDER BY id_clave",
                (id_institucion,)
            ).fetchall()
        return [dict(r) | {"usada": bool(r["usada"])} for r in rows]

    def eliminar_clave_vecino(self, id_clave: int) -> bool:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM claves_vecinos WHERE id_clave=?", (id_clave,))
        return cur.rowcount > 0

    # ── VECINOS ──────────────────────────────────────────────

    def registrar_vecino(self, data: dict) -> dict:
        # ¿Ya existe? → actualizar teléfono, dirección y más
        existente = self.buscar_vecino_por_identificacion(data["num_identificacion"], data["id_institucion"])
        if existente:
            campos_editar = {k: data[k] for k in ("nombre","telefono","direccion","sexo","edad","correo") if k in data}
            sets = [f"{k}=?" for k in campos_editar]
            vals = list(campos_editar.values()) + [existente["id_vecino"]]
            if sets:
                with get_conn() as conn:
                    conn.execute(f"UPDATE vecinos SET {', '.join(sets)} WHERE id_vecino=?", vals)
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
            conn.execute("""
                INSERT INTO vecinos
                (id_vecino,id_institucion,nombre,telefono,num_identificacion,direccion,sexo,edad,correo,codigo_vecino,clave_acceso,activo,fecha_registro)
                VALUES (:id_vecino,:id_institucion,:nombre,:telefono,:num_identificacion,:direccion,:sexo,:edad,:correo,:codigo_vecino,:clave_acceso,1,:fecha_registro)
            """, vecino)
            # Marcar clave usada
            if data.get("clave_acceso"):
                conn.execute(
                    "UPDATE claves_vecinos SET usada=1, id_vecino=? WHERE UPPER(clave)=UPPER(?)",
                    (vecino["id_vecino"], data["clave_acceso"])
                )
        return vecino

    def buscar_vecino_por_identificacion(self, num_id: str, id_institucion: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM vecinos WHERE id_institucion=? AND UPPER(num_identificacion)=UPPER(?)",
                (id_institucion, num_id)
            ).fetchone()
        if not row: return None
        return dict(row) | {"activo": bool(row["activo"])}

    def obtener_vecino_por_clave(self, clave: str) -> Optional[dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM vecinos WHERE UPPER(clave_acceso)=UPPER(?)", (clave,)
            ).fetchone()
        if not row: return None
        return dict(row) | {"activo": bool(row["activo"])}

    @property
    def vecinos(self):
        """Compatibilidad con código que itera db.vecinos.values()"""
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM vecinos").fetchall()
        return {r["id_vecino"]: dict(r) | {"activo": bool(r["activo"])} for r in rows}

    def listar_vecinos(self, id_institucion: str) -> List[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM vecinos WHERE id_institucion=? ORDER BY fecha_registro",
                (id_institucion,)
            ).fetchall()
        return [dict(r) | {"activo": bool(r["activo"])} for r in rows]

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
            conn.execute("""
                INSERT INTO emergencias
                (id_emergencia,id_institucion,id_vecino,nombre_vecino,telefono_vecino,num_identificacion,
                 direccion_vecino,gps_latitud,gps_longitud,direccion_aproximada,estatus,notas_operador,fecha_creacion,fecha_atencion)
                VALUES (:id_emergencia,:id_institucion,:id_vecino,:nombre_vecino,:telefono_vecino,:num_identificacion,
                        :direccion_vecino,:gps_latitud,:gps_longitud,:direccion_aproximada,:estatus,:notas_operador,:fecha_creacion,:fecha_atencion)
            """, e)
        return e

    def listar_emergencias(self, id_institucion: str, estatus: str = None) -> List[dict]:
        sql = "SELECT * FROM emergencias WHERE id_institucion=?"
        params: list = [id_institucion]
        if estatus:
            sql += " AND estatus=?"
            params.append(estatus)
        sql += " ORDER BY fecha_creacion DESC"
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def actualizar_estatus_emergencia(self, id_emergencia: str, estatus: str, notas: str = None) -> Optional[dict]:
        fecha_atencion = datetime.now().isoformat() if estatus in ("ATENDIDA","FALSA_ALARMA","CANCELADA") else None
        with get_conn() as conn:
            conn.execute("""
                UPDATE emergencias SET estatus=?, notas_operador=COALESCE(?,notas_operador), fecha_atencion=COALESCE(?,fecha_atencion)
                WHERE id_emergencia=?
            """, (estatus, notas, fecha_atencion, id_emergencia))
            row = conn.execute("SELECT * FROM emergencias WHERE id_emergencia=?", (id_emergencia,)).fetchone()
        return dict(row) if row else None

    def stats_institucion(self, id_institucion: str) -> dict:
        with get_conn() as conn:
            total    = conn.execute("SELECT COUNT(*) FROM emergencias WHERE id_institucion=?", (id_institucion,)).fetchone()[0]
            activas  = conn.execute("SELECT COUNT(*) FROM emergencias WHERE id_institucion=? AND estatus='ACTIVA'", (id_institucion,)).fetchone()[0]
            camino   = conn.execute("SELECT COUNT(*) FROM emergencias WHERE id_institucion=? AND estatus='EN_CAMINO'", (id_institucion,)).fetchone()[0]
            atend    = conn.execute("SELECT COUNT(*) FROM emergencias WHERE id_institucion=? AND estatus='ATENDIDA'", (id_institucion,)).fetchone()[0]
            vecinos  = conn.execute("SELECT COUNT(*) FROM vecinos WHERE id_institucion=?", (id_institucion,)).fetchone()[0]
        return {"total": total, "activas": activas, "en_camino": camino, "atendidas": atend, "vecinos_registrados": vecinos}


# Inicializar tablas y objeto global
init_db()
db = Database()
