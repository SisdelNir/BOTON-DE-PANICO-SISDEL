"""Router: Emergencias (scoped por institución)"""
from fastapi import APIRouter, HTTPException
from models import EmergenciaCreate, EmergenciaResponse, EstatusUpdate, StatsResponse
from database import db

router = APIRouter(prefix="/api/emergencias", tags=["Emergencias"])


@router.post("/", response_model=EmergenciaResponse, status_code=201)
async def crear(data: EmergenciaCreate):
    if not db.obtener_institucion(data.id_institucion):
        raise HTTPException(404, "Institución no encontrada")
    return db.crear_emergencia(data.model_dump())


@router.get("/{id_institucion}", response_model=list[EmergenciaResponse])
async def listar(id_institucion: str, estatus: str = None):
    return db.listar_emergencias(id_institucion, estatus)


@router.get("/{id_institucion}/stats", response_model=StatsResponse)
async def stats(id_institucion: str):
    return db.stats_institucion(id_institucion)


@router.patch("/{id_emergencia}/estatus", response_model=EmergenciaResponse)
async def actualizar_estatus(id_emergencia: str, data: EstatusUpdate):
    e = db.actualizar_estatus_emergencia(id_emergencia, data.estatus, data.notas)
    if not e:
        raise HTTPException(404, "Emergencia no encontrada")
    return e
