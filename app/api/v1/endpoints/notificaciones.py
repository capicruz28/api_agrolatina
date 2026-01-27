# app/api/v1/endpoints/notificaciones.py
"""
Endpoints para gestión de notificaciones push.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from app.schemas.vacaciones_permisos import (
    DispositivoRegistroToken,
    DispositivoRegistroResponse
)
from app.services.notificaciones_service import NotificacionesService
from app.api.deps import get_current_active_user
from app.schemas.usuario import UsuarioReadWithRoles
from app.api.v1.endpoints.vacaciones_permisos_mobile import obtener_codigo_trabajador

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/registrar-token",
    response_model=DispositivoRegistroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar token de dispositivo",
    description="Registra o actualiza el token FCM de un dispositivo asociado a un usuario"
)
async def registrar_token_dispositivo(
    dispositivo_data: DispositivoRegistroToken,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Registra o actualiza el token FCM de un dispositivo.
    
    Validaciones:
    - El código_trabajador debe corresponder al usuario autenticado
    - El token_fcm debe ser único
    - La plataforma debe ser 'A' (Android) o 'I' (iOS)
    """
    try:
        # Verificar que el código de trabajador corresponde al usuario autenticado
        codigo_trabajador_usuario = obtener_codigo_trabajador(current_user)
        
        if dispositivo_data.codigo_trabajador != codigo_trabajador_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El código de trabajador no corresponde al usuario autenticado"
            )
        
        # Registrar o actualizar token
        resultado = await NotificacionesService.registrar_token_dispositivo(
            token_fcm=dispositivo_data.token_fcm,
            codigo_trabajador=dispositivo_data.codigo_trabajador,
            plataforma=dispositivo_data.plataforma,
            modelo_dispositivo=dispositivo_data.modelo_dispositivo,
            version_app=dispositivo_data.version_app,
            version_so=dispositivo_data.version_so
        )
        
        logger.info(
            f"Token registrado/actualizado para usuario {current_user.nombre_usuario}, "
            f"dispositivo {resultado.get('id_dispositivo')}"
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error registrando token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar token del dispositivo"
        )
