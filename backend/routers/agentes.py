"""Router: Agentes de Seguridad (scoped por institución)"""
from fastapi import APIRouter, HTTPException
from models import AgenteCreate, AgenteResponse
from database import db, registrar_agente, listar_agentes, obtener_agente

router = APIRouter(prefix="/api/agentes", tags=["Agentes"])


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
