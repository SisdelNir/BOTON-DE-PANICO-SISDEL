"""
Botón de Pánico SISDEL — Base de Datos Multi-Institucional
Tablas: instituciones, claves_vecinos, vecinos, emergencias
"""

import uuid, random, string
from datetime import datetime
from typing import List, Optional, Dict

CLAVE_PROGRAMADOR = "1122"
NOMBRE_SISTEMA    = "Botón de Pánico SISDEL"


def generar_clave_6(nombre: str = None) -> str:
    """
    Clave de 6 chars para institución:
      L1 = primera letra del nombre
      L2 = letra al azar
      L3 = última letra del nombre
      N1 N2 N3 = dígitos al azar
    Ejemplo: 'MUNICIPIO DE OLINTEQUE' → M?E###
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


class Database:
    def __init__(self):
        self.instituciones: Dict[str, dict] = {}
        self.claves_vecinos: List[dict] = []
        self.vecinos: Dict[str, dict] = {}
        self.emergencias: List[dict] = []

        self._clave_seq = 1
        self._seed()

    def _seed(self):
        """Institución demo inicial."""
        self.crear_institucion({
            "nombre_institucion": "Colonia Demo",
            "nombre_admin": "Admin Demo",
            "telefono": "5550000000",
            "correo": "demo@sisdel.mx",
            "direccion": "Calle Principal #1"
        })

    # ── INSTITUCIONES ────────────────────────────────────────

    def crear_institucion(self, data: dict) -> dict:
        inst = {
            "id_institucion": str(uuid.uuid4()),
            "nombre_institucion": data["nombre_institucion"],
            "nombre_admin":       data["nombre_admin"],
            "telefono":           data.get("telefono", ""),
            "correo":             data.get("correo", ""),
            "direccion":          data.get("direccion", ""),
            "clave_acceso":       generar_clave_6(data["nombre_institucion"]),
            "activo":             True,
            "fecha_registro":     datetime.now().isoformat(),
        }
        self.instituciones[inst["id_institucion"]] = inst
        return inst

    def listar_instituciones(self) -> List[dict]:
        return list(self.instituciones.values())

    def obtener_institucion(self, id_inst: str) -> Optional[dict]:
        return self.instituciones.get(id_inst)

    def obtener_institucion_por_clave(self, clave: str) -> Optional[dict]:
        for inst in self.instituciones.values():
            if inst["clave_acceso"].upper() == clave.upper() and inst["activo"]:
                return inst
        return None

    def toggle_institucion(self, id_inst: str) -> Optional[dict]:
        inst = self.instituciones.get(id_inst)
        if inst:
            inst["activo"] = not inst["activo"]
        return inst

    def regenerar_clave_institucion(self, id_inst: str) -> Optional[dict]:
        inst = self.instituciones.get(id_inst)
        if inst:
            # Mantiene la regla: primera y última letra del nombre original
            inst["clave_acceso"] = generar_clave_6(inst["nombre_institucion"])
        return inst

    def editar_institucion(self, id_inst: str, campos: dict) -> Optional[dict]:
        inst = self.instituciones.get(id_inst)
        if not inst:
            return None
        for k, v in campos.items():
            if v is not None and k in inst:
                inst[k] = v
        return inst

    def eliminar_institucion(self, id_inst: str) -> bool:
        if id_inst in self.instituciones:
            del self.instituciones[id_inst]
            return True
        return False



    # ── CLAVES VECINOS ───────────────────────────────────────

    def generar_clave_vecino(self, id_institucion: str, descripcion: str = "") -> dict:
        clave = {
            "id_clave":        self._clave_seq,
            "clave":           generar_clave_6(),
            "id_institucion":  id_institucion,
            "descripcion":     descripcion,
            "usada":           False,
            "id_vecino":       None,
            "fecha_creacion":  datetime.now().isoformat(),
        }
        self._clave_seq += 1
        self.claves_vecinos.append(clave)
        return clave

    def validar_clave_vecino(self, clave: str, id_institucion: str = None) -> Optional[dict]:
        for c in self.claves_vecinos:
            match_clave = c["clave"].upper() == clave.upper()
            match_inst  = (id_institucion is None) or (c["id_institucion"] == id_institucion)
            if match_clave and match_inst:
                return c
        return None

    def listar_claves_vecinos(self, id_institucion: str) -> List[dict]:
        return [c for c in self.claves_vecinos if c["id_institucion"] == id_institucion]

    def eliminar_clave_vecino(self, id_clave: int) -> bool:
        for i, c in enumerate(self.claves_vecinos):
            if c["id_clave"] == id_clave:
                self.claves_vecinos.pop(i)
                return True
        return False

    # ── VECINOS ──────────────────────────────────────────────

    def registrar_vecino(self, data: dict) -> dict:
        # Si ya existe por (id_institucion, num_identificacion) → actualizar
        for v in self.vecinos.values():
            if (v["id_institucion"] == data["id_institucion"] and
                    v["num_identificacion"] == data["num_identificacion"]):
                for k in ("nombre","telefono","direccion","sexo","edad","correo"):
                    if k in data:
                        v[k] = data[k]
                return v
        vecino = {
            "id_vecino":         str(uuid.uuid4()),
            "id_institucion":    data["id_institucion"],
            "nombre":            data["nombre"],
            "telefono":          data["telefono"],
            "num_identificacion":data["num_identificacion"],
            "direccion":         data.get("direccion", ""),
            "sexo":              data.get("sexo", ""),
            "edad":              data.get("edad", 0),
            "correo":            data.get("correo", ""),
            "codigo_vecino":     generar_clave_6(data["nombre"]),
            "clave_acceso":      data.get("clave_acceso", ""),
            "activo":            True,
            "fecha_registro":    datetime.now().isoformat(),
        }
        self.vecinos[vecino["id_vecino"]] = vecino
        # Marcar clave como usada
        for c in self.claves_vecinos:
            if c["clave"].upper() == data.get("clave_acceso","").upper():
                c["usada"] = True
                c["id_vecino"] = vecino["id_vecino"]
                break
        return vecino

    def buscar_vecino_por_identificacion(self, num_id: str, id_institucion: str) -> Optional[dict]:
        """Busca un vecino por su num_identificacion dentro de una institución."""
        for v in self.vecinos.values():
            if (v["id_institucion"] == id_institucion and
                    v["num_identificacion"].upper() == num_id.upper()):
                return v
        return None

    def obtener_vecino_por_clave(self, clave: str) -> Optional[dict]:
        for v in self.vecinos.values():
            if v.get("clave_acceso","").upper() == clave.upper():
                return v
        return None

    def listar_vecinos(self, id_institucion: str) -> List[dict]:
        return [v for v in self.vecinos.values() if v["id_institucion"] == id_institucion]

    # ── EMERGENCIAS ──────────────────────────────────────────

    def crear_emergencia(self, data: dict) -> dict:
        e = {
            "id_emergencia":    str(uuid.uuid4()),
            "id_institucion":   data["id_institucion"],
            "id_vecino":        data.get("id_vecino"),
            "nombre_vecino":    data.get("nombre_vecino","Desconocido"),
            "telefono_vecino":  data.get("telefono_vecino",""),
            "num_identificacion":data.get("num_identificacion",""),
            "direccion_vecino": data.get("direccion_vecino",""),
            "gps_latitud":      data.get("gps_latitud"),
            "gps_longitud":     data.get("gps_longitud"),
            "direccion_aproximada": data.get("direccion_aproximada",""),
            "estatus":          "ACTIVA",
            "notas_operador":   None,
            "fecha_creacion":   datetime.now().isoformat(),
            "fecha_atencion":   None,
        }
        self.emergencias.append(e)
        return e

    def listar_emergencias(self, id_institucion: str, estatus: str = None) -> List[dict]:
        result = [e for e in self.emergencias if e["id_institucion"] == id_institucion]
        if estatus:
            result = [e for e in result if e["estatus"] == estatus]
        return sorted(result, key=lambda x: x["fecha_creacion"], reverse=True)

    def actualizar_estatus_emergencia(self, id_emergencia: str, estatus: str, notas: str = None) -> Optional[dict]:
        for e in self.emergencias:
            if e["id_emergencia"] == id_emergencia:
                e["estatus"] = estatus
                if notas:
                    e["notas_operador"] = notas
                if estatus in ("ATENDIDA","FALSA_ALARMA","CANCELADA"):
                    e["fecha_atencion"] = datetime.now().isoformat()
                return e
        return None

    def stats_institucion(self, id_institucion: str) -> dict:
        todas = [e for e in self.emergencias if e["id_institucion"] == id_institucion]
        return {
            "total":               len(todas),
            "activas":             sum(1 for e in todas if e["estatus"] == "ACTIVA"),
            "en_camino":           sum(1 for e in todas if e["estatus"] == "EN_CAMINO"),
            "atendidas":           sum(1 for e in todas if e["estatus"] == "ATENDIDA"),
            "vecinos_registrados": len(self.listar_vecinos(id_institucion)),
        }


db = Database()
