"""Router: Programador — gestión de instituciones (clave maestra 1122)"""
from fastapi import APIRouter, HTTPException
from models import InstitucionCreate, InstitucionUpdate, InstitucionResponse, LoginInstRequest, LoginInstResponse
from database import db, CLAVE_PROGRAMADOR

router = APIRouter(prefix="/api/programador", tags=["Programador"])


@router.post("/login", response_model=LoginInstResponse)
async def login(data: LoginInstRequest):
    clave = data.clave.strip()

    # ¿Es clave de programador?
    if clave == CLAVE_PROGRAMADOR:
        return LoginInstResponse(success=True, message="Acceso programador", tipo="programador")

    # ¿Es clave de institución?
    inst = db.obtener_institucion_por_clave(clave)
    if inst:
        return LoginInstResponse(
            success=True, message="Acceso institución", tipo="institucion",
            institucion=InstitucionResponse(**inst)
        )

    # ¿Es código de vecino (codigo_vecino)?
    for v in db.vecinos.values():
        if v.get("codigo_vecino", "").upper() == clave.upper():
            return LoginInstResponse(
                success=True, message="Acceso vecino",
                tipo="vecino", id_institucion=v["id_institucion"],
                num_identificacion=v["num_identificacion"]
            )

    # ¿Es número de identificación de vecino?
    for v in db.vecinos.values():
        if v.get("num_identificacion", "").upper() == clave.upper():
            return LoginInstResponse(
                success=True, message="Acceso vecino",
                tipo="vecino", id_institucion=v["id_institucion"],
                num_identificacion=v["num_identificacion"]
            )

    # ¿Es clave de acceso de vecino (clave_acceso)?
    clave_obj = db.validar_clave_vecino(clave)
    if clave_obj:
        return LoginInstResponse(
            success=True, message="Acceso vecino",
            tipo="vecino", id_institucion=clave_obj["id_institucion"]
        )

    return LoginInstResponse(success=False, message="Clave inválida")


@router.get("/instituciones", response_model=list[InstitucionResponse])
async def listar():
    return db.listar_instituciones()


@router.post("/instituciones", response_model=InstitucionResponse, status_code=201)
async def crear(data: InstitucionCreate):
    return db.crear_institucion(data.model_dump())


@router.patch("/instituciones/{id_inst}/toggle", response_model=InstitucionResponse)
async def toggle(id_inst: str):
    inst = db.toggle_institucion(id_inst)
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    return inst


@router.patch("/instituciones/{id_inst}/regenerar-clave", response_model=InstitucionResponse)
async def regenerar(id_inst: str):
    inst = db.regenerar_clave_institucion(id_inst)
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    return inst


@router.put("/instituciones/{id_inst}", response_model=InstitucionResponse)
async def editar(id_inst: str, data: InstitucionUpdate):
    inst = db.editar_institucion(id_inst, data.model_dump(exclude_unset=True))
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    return inst


@router.delete("/instituciones/{id_inst}", status_code=204)
async def eliminar(id_inst: str):
    ok = db.eliminar_institucion(id_inst)
    if not ok:
        raise HTTPException(404, "Institución no encontrada")
