"""Router: Pilotos — CRUD de pilotos para empresas de seguridad"""
from fastapi import APIRouter, HTTPException, Body
from models import PilotoCreate
from database import (
    registrar_piloto, listar_pilotos, obtener_piloto,
    actualizar_piloto, obtener_contactos_piloto
)

router = APIRouter(prefix="/api/pilotos", tags=["Pilotos"])


@router.post("/", status_code=201)
async def crear_o_actualizar(data: PilotoCreate):
    p = registrar_piloto(data.model_dump())
    return p


@router.get("/{id_empresa}")
async def listar(id_empresa: str):
    return listar_pilotos(id_empresa)


@router.get("/detalle/{id_piloto}")
async def detalle(id_piloto: str):
    p = obtener_piloto(id_piloto)
    if not p:
        raise HTTPException(404, "Piloto no encontrado")
    return p


@router.put("/{id_piloto}")
async def actualizar(id_piloto: str, data: dict = Body(...)):
    p = actualizar_piloto(id_piloto, data)
    if not p:
        raise HTTPException(404, "Piloto no encontrado")
    return p


@router.get("/{id_piloto}/contactos")
async def contactos(id_piloto: str):
    return obtener_contactos_piloto(id_piloto)
