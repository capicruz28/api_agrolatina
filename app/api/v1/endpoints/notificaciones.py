# app/api/v1/endpoints/notificaciones.py
"""
Endpoints para gestión de notificaciones push.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
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


@router.get(
    "/estado-firebase",
    summary="Verificar estado de Firebase",
    description="Endpoint para verificar si Firebase Admin SDK está inicializado correctamente"
)
async def verificar_estado_firebase(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Endpoint para verificar el estado de Firebase Admin SDK.
    """
    try:
        import firebase_admin
        import os
        import json
        from app.services.notificaciones_service import NotificacionesService
        
        # Obtener variables de entorno
        firebase_cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Si no hay ruta configurada, buscar archivo JSON en la raíz del proyecto
        if not firebase_cred_path or not os.path.exists(firebase_cred_path):
            import pathlib
            current_file = pathlib.Path(__file__).resolve()
            # Subir 5 niveles: endpoints -> v1 -> api -> app -> raíz
            project_root = current_file.parent.parent.parent.parent.parent
            
            json_files = list(project_root.glob("*firebase-adminsdk*.json"))
            app_dir = project_root / "app"
            if app_dir.exists():
                json_files.extend(list(app_dir.glob("*firebase-adminsdk*.json")))
            
            if json_files:
                firebase_cred_path = str(json_files[0].resolve())
        
        # Intentar leer project_id del JSON si existe
        project_id_from_json = None
        if firebase_cred_path and os.path.exists(firebase_cred_path):
            try:
                with open(firebase_cred_path, 'r', encoding='utf-8') as f:
                    cred_data = json.load(f)
                    project_id_from_json = cred_data.get('project_id')
            except Exception as e:
                logger.warning(f"No se pudo leer project_id del JSON: {str(e)}")
        
        # Verificar si Firebase está disponible
        try:
            app = firebase_admin.get_app()
            project_id = getattr(app, 'project_id', None)
            
            return {
                "firebase_disponible": True,
                "firebase_inicializado": True,
                "project_id": project_id,
                "project_id_configurado": project_id is not None,
                "credential_path": firebase_cred_path if firebase_cred_path else "No configurado",
                "project_id_env": firebase_project_id if firebase_project_id else "No configurado",
                "project_id_json": project_id_from_json if project_id_from_json else "No encontrado en JSON",
                "mensaje": "Firebase Admin SDK está inicializado" + (" pero SIN project_id" if not project_id else " correctamente"),
                "accion_requerida": "Reiniciar servidor con FIREBASE_PROJECT_ID configurado" if not project_id else None
            }
        except ValueError:
            # Firebase no está inicializado
            return {
                "firebase_disponible": True,
                "firebase_inicializado": False,
                "mensaje": "Firebase Admin SDK no está inicializado",
                "credential_path": firebase_cred_path if firebase_cred_path else "No configurado",
                "project_id_env": firebase_project_id if firebase_project_id else "No configurado",
                "project_id_json": project_id_from_json if project_id_from_json else "No encontrado en JSON",
                "accion_requerida": "Configurar FIREBASE_CREDENTIALS_PATH y FIREBASE_PROJECT_ID, luego reiniciar servidor"
            }
    except ImportError:
        return {
            "firebase_disponible": False,
            "firebase_inicializado": False,
            "mensaje": "firebase-admin no está instalado"
        }
    except Exception as e:
        logger.exception(f"Error verificando estado de Firebase: {str(e)}")
        return {
            "firebase_disponible": True,
            "firebase_inicializado": False,
            "mensaje": f"Error: {str(e)}"
        }


@router.post(
    "/reinicializar-firebase",
    summary="Reinicializar Firebase",
    description="Endpoint para reinicializar Firebase Admin SDK con Project ID"
)
async def reinicializar_firebase(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Endpoint para reinicializar Firebase Admin SDK con Project ID.
    """
    try:
        import firebase_admin
        import os
        import json
        from firebase_admin import credentials
        from app.services.notificaciones_service import NotificacionesService
        
        # Obtener variables de entorno
        firebase_cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Si no hay ruta configurada o el archivo no existe, buscar archivo JSON en la raíz del proyecto
        if not firebase_cred_path or not os.path.exists(firebase_cred_path):
            import pathlib
            # Calcular la raíz del proyecto: desde app/api/v1/endpoints/notificaciones.py
            # Subir 5 niveles: endpoints -> v1 -> api -> app -> raíz
            current_file = pathlib.Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent.parent  # 5 niveles para llegar a la raíz
            
            logger.info(f"Buscando archivo JSON de Firebase en: {project_root}")
            
            # Buscar archivos JSON de Firebase con diferentes patrones
            patterns = [
                "*firebase-adminsdk*.json",
                "*firebase*.json",
                "serviceAccountKey.json"
            ]
            
            json_files = []
            for pattern in patterns:
                json_files.extend(list(project_root.glob(pattern)))
                if json_files:
                    break
            
            # También buscar en el directorio app por si acaso
            if not json_files:
                app_dir = project_root / "app"
                if app_dir.exists():
                    for pattern in patterns:
                        json_files.extend(list(app_dir.glob(pattern)))
                        if json_files:
                            break
            
            if json_files:
                firebase_cred_path = str(json_files[0].resolve())
                logger.info(f"[OK] Archivo JSON de Firebase encontrado automáticamente: {firebase_cred_path}")
            else:
                # Listar archivos en la raíz para debug
                try:
                    all_files = [f.name for f in project_root.iterdir() if f.is_file() and f.suffix == '.json']
                    logger.warning(f"[WARN] No se encontraron archivos JSON de Firebase. Archivos JSON encontrados en raíz: {all_files}")
                except Exception as e:
                    logger.warning(f"Error listando archivos: {str(e)}")
        
        # Verificar que el archivo existe antes de continuar
        if not firebase_cred_path or not os.path.exists(firebase_cred_path):
            error_msg = f"No se encontró el archivo JSON de credenciales de Firebase."
            if firebase_cred_path:
                error_msg += f" Ruta buscada: {firebase_cred_path}"
            error_msg += f" Busca el archivo en la raíz del proyecto (d:\\api_psf\\) o configura FIREBASE_CREDENTIALS_PATH."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Intentar leer project_id del JSON si existe
        project_id_from_json = None
        try:
            with open(firebase_cred_path, 'r', encoding='utf-8') as f:
                cred_data = json.load(f)
                project_id_from_json = cred_data.get('project_id')
                if project_id_from_json:
                    logger.info(f"[OK] Project ID leído del JSON: {project_id_from_json}")
                else:
                    logger.warning("[WARN] El archivo JSON no contiene 'project_id'")
        except json.JSONDecodeError as e:
            logger.error(f"Error: El archivo JSON no es válido: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo JSON no es válido: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error leyendo el archivo JSON: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo leer el archivo JSON: {str(e)}"
            )
        
        # Determinar project_id a usar
        project_id = firebase_project_id or project_id_from_json
        
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró project_id. Configura FIREBASE_PROJECT_ID o asegúrate de que el archivo JSON contenga 'project_id'. Archivo: {firebase_cred_path}"
            )
        
        # Eliminar app existente si existe
        try:
            app = firebase_admin.get_app()
            firebase_admin.delete_app(app)
            logger.info("App de Firebase eliminada para reinicialización")
        except ValueError:
            pass  # No hay app para eliminar
        
        # Reinicializar Firebase
        if firebase_cred_path and os.path.exists(firebase_cred_path):
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred, {'projectId': project_id})
            logger.info(f"[OK] Firebase Admin SDK reinicializado con project_id: {project_id}")
        else:
            firebase_admin.initialize_app(options={'projectId': project_id})
            logger.info(f"[OK] Firebase Admin SDK reinicializado con project_id: {project_id}")
        
        return {
            "success": True,
            "mensaje": f"Firebase Admin SDK reinicializado correctamente con project_id: {project_id}",
            "project_id": project_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reinicializando Firebase: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al reinicializar Firebase: {str(e)}"
        )


@router.post(
    "/test-envio",
    summary="Probar envío de notificación",
    description="Endpoint de prueba para verificar que el envío de notificaciones funciona"
)
async def test_envio_notificacion(
    token_fcm: str = Query(..., description="Token FCM a probar"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """
    Endpoint de prueba para verificar que el envío de notificaciones funciona.
    Usar con el token_fcm del aprobador desde la base de datos.
    """
    try:
        # Usar el servicio de notificaciones que maneja mejor los errores
        resultado = NotificacionesService.enviar_notificacion_multicast(
            tokens=[token_fcm],
            titulo="Prueba de Notificación",
            cuerpo="Esta es una notificación de prueba desde el backend",
            data={
                "tipo_solicitud": "V",
                "id_solicitud": "999",
                "tipo": "test"
            }
        )
        
        if resultado.get('enviado'):
            logger.info(f"Notificación de prueba enviada exitosamente")
            return {
                "success": True,
                "message": "Notificación enviada exitosamente",
                "resultado": resultado
            }
        else:
            logger.error(f"No se pudo enviar notificación de prueba: {resultado.get('mensaje')}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo enviar notificación: {resultado.get('mensaje', 'Error desconocido')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error en prueba de notificación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar notificación de prueba: {str(e)}"
        )
