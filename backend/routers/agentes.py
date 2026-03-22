"""Router: Agentes de Seguridad (scoped por institución)"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models import AgenteCreate, AgenteResponse
from database import (db, registrar_agente, listar_agentes, obtener_agente,
                      asignar_agente_emergencia, obtener_asignaciones_emergencia,
                      casos_por_agente)

router = APIRouter(prefix="/api/agentes", tags=["Agentes"])


class AsignarRequest(BaseModel):
    id_emergencia: str
    id_institucion: str
    num_identificacion: str
    slot: int  # 1-4


@router.post("/", response_model=AgenteResponse, status_code=201)
async def crear_agente(data: AgenteCreate):
    inst = db.obtener_institucion(data.id_institucion)
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    return registrar_agente(data.model_dump(), inst["nombre_institucion"])


@router.get("/{id_institucion}", response_model=list[AgenteResponse])
async def listar(id_institucion: str):
    return listar_agentes(id_institucion)


@router.get("/{id_institucion}/{num_identificacion}", response_model=AgenteResponse)
async def obtener(id_institucion: str, num_identificacion: str):
    agente = obtener_agente(id_institucion, num_identificacion)
    if not agente:
        raise HTTPException(404, "Agente no encontrado")
    return agente


# ── ASIGNACIONES ─────────────────────────────────

@router.post("/asignar")
async def asignar(data: AsignarRequest):
    """Asigna un agente a una emergencia en un slot (1-4)."""
    if data.slot < 1 or data.slot > 4:
        raise HTTPException(400, "Slot debe ser entre 1 y 4")
    result = asignar_agente_emergencia(
        data.id_emergencia, data.id_institucion, data.num_identificacion, data.slot
    )
    return result


@router.get("/asignaciones/{id_emergencia}")
async def get_asignaciones(id_emergencia: str):
    """Obtiene los agentes asignados a una emergencia."""
    return obtener_asignaciones_emergencia(id_emergencia)


@router.get("/mis-casos/{id_institucion}/{identificador}")
async def mis_casos(id_institucion: str, identificador: str):
    """Consulta los casos asignados a un agente (por doc o código)."""
    resultado = casos_por_agente(id_institucion, identificador)
    if not resultado:
        raise HTTPException(404, "Agente no encontrado o sin casos")
    return resultado
