from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_user
from app.schemas.usuario import UsuarioReadWithRoles
from app.core.logging_config import get_logger
from app.core.exceptions import CustomException
from app.db.queries import execute_auth_query

from app.services.aviso_ap_service import AvisoApService
from app.schemas.aviso_ap import (
    AvisoApPendienteResponse,
    AvisoApVisualizadoResponse,
    AvisoApAceptarRequest,
    AvisoApAceptarResponse,
)

logger = get_logger(__name__)
router = APIRouter()


def obtener_codigo_trabajador(current_user: UsuarioReadWithRoles) -> str:
    """
    Obtiene ctraba de la misma manera que SELECT_DOCUMENTO_PAGO_POR_ANIO:
    leyendo codigo_trabajador_externo desde la tabla usuario por usuario_id.
    """
    query = """
        SELECT codigo_trabajador_externo
        FROM usuario
        WHERE usuario_id = ? AND es_eliminado = 0
    """
    resultado = execute_auth_query(query, (current_user.usuario_id,))

    if not resultado or not resultado.get("codigo_trabajador_externo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario no tiene código de trabajador asociado. Contacte al administrador.",
        )

    return str(resultado["codigo_trabajador_externo"]).strip()


@router.get(
    "/ap/pendiente",
    response_model=AvisoApPendienteResponse,
    summary="Obtener aviso AP pendiente",
    description="Obtiene el aviso general AP pendiente del trabajador autenticado (incluye PDF base64).",
    dependencies=[Depends(get_current_active_user)],
)
async def get_aviso_ap_pendiente(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user),
):
    try:
        codigo_trabajador = obtener_codigo_trabajador(current_user)
        return await AvisoApService.obtener_aviso_pendiente(codigo_trabajador)
    except HTTPException:
        raise
    except CustomException as ce:
        logger.warning(f"Error de negocio obteniendo aviso AP pendiente: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado obteniendo aviso AP pendiente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el aviso pendiente",
        )


@router.post(
    "/ap/visualizado",
    response_model=AvisoApVisualizadoResponse,
    summary="Marcar aviso AP como visualizado",
    description="Actualiza fvisual con fecha/hora actual si el aviso AP está pendiente y aún no fue visualizado.",
    dependencies=[Depends(get_current_active_user)],
)
async def marcar_aviso_ap_visualizado(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user),
):
    try:
        codigo_trabajador = obtener_codigo_trabajador(current_user)
        return await AvisoApService.marcar_visualizado(codigo_trabajador)
    except HTTPException:
        raise
    except CustomException as ce:
        logger.warning(f"Error de negocio marcando aviso AP visualizado: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado marcando aviso AP visualizado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar visualización del aviso",
        )


@router.post(
    "/ap/aceptar",
    response_model=AvisoApAceptarResponse,
    summary="Aceptar aviso AP (Conforme)",
    description="Actualiza faprob con fecha/hora actual y saprob='S' cuando el usuario acepta el aviso AP.",
    dependencies=[Depends(get_current_active_user)],
)
async def aceptar_aviso_ap(
    payload: AvisoApAceptarRequest,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user),
):
    if payload.conforme is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe marcar 'Conforme' para aceptar el aviso.",
        )

    try:
        codigo_trabajador = obtener_codigo_trabajador(current_user)
        return await AvisoApService.aceptar_aviso(codigo_trabajador)
    except HTTPException:
        raise
    except CustomException as ce:
        logger.warning(f"Error de negocio aceptando aviso AP: {ce.detail}")
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado aceptando aviso AP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al aceptar el aviso",
        )

