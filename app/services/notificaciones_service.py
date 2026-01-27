# app/services/notificaciones_service.py
"""
Servicio para manejo de notificaciones push usando Firebase Cloud Messaging.
"""

import logging
from typing import List, Dict, Any, Optional
from app.db.queries import (
    SELECT_DISPOSITIVO_BY_TOKEN,
    INSERT_DISPOSITIVO,
    UPDATE_DISPOSITIVO_TOKEN,
    SELECT_TOKENS_APROBADORES,
    SELECT_TOKENS_BY_CODIGOS_TRABAJADORES,
    SELECT_AREA_TRABAJADOR,
    SELECT_APROBADORES_POR_TRABAJADOR
)
from app.db.queries import execute_query, execute_insert, execute_update
from app.core.exceptions import ServiceError, DatabaseError
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("firebase-admin no est? instalado. Las notificaciones push no funcionar?n.")


class NotificacionesService(BaseService):
    """Servicio para manejo de notificaciones push"""

    @staticmethod
    def inicializar_firebase(credential_path: Optional[str] = None, project_id: Optional[str] = None):
        """
        Inicializa Firebase Admin SDK.
        
        Args:
            credential_path: Ruta al archivo JSON de credenciales de Firebase.
                            Si es None, intenta usar variable de entorno o inicializaci?n previa.
            project_id: Project ID de Firebase (opcional, se extrae del JSON si no se proporciona)
        """
        if not FIREBASE_AVAILABLE:
            logger.error("Firebase Admin SDK no est? disponible")
            return False
        
        try:
            # Verificar si ya est? inicializado
            try:
                app = firebase_admin.get_app()
                logger.info("Firebase Admin SDK ya est? inicializado")
                return True
            except ValueError:
                # No est? inicializado, proceder a inicializar
                pass
            
            import json
            import os
            
            # Intentar obtener project_id del archivo JSON si no se proporciona
            if credential_path and os.path.exists(credential_path) and not project_id:
                try:
                    with open(credential_path, 'r', encoding='utf-8') as f:
                        cred_data = json.load(f)
                        project_id = cred_data.get('project_id')
                        if project_id:
                            logger.info(f"Project ID extra?do del archivo de credenciales: {project_id}")
                except Exception as e:
                    logger.warning(f"No se pudo extraer project_id del archivo JSON: {str(e)}")
            
            # Intentar obtener project_id de variable de entorno si no est? disponible
            if not project_id:
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('FIREBASE_PROJECT_ID')
                if project_id:
                    logger.info(f"Project ID obtenido de variable de entorno: {project_id}")
            
            # Inicializar Firebase
            if credential_path and os.path.exists(credential_path):
                cred = credentials.Certificate(credential_path)
                # Firebase Admin SDK v7.0+ requiere project_id explícito para Cloud Messaging
                # Intentar extraerlo del JSON si aún no lo tenemos
                if not project_id:
                    try:
                        with open(credential_path, 'r', encoding='utf-8') as f:
                            cred_data = json.load(f)
                            project_id = cred_data.get('project_id')
                            if project_id:
                                logger.info(f"Project ID extraído del JSON durante inicialización: {project_id}")
                    except Exception as e:
                        logger.warning(f"No se pudo leer project_id del JSON durante inicialización: {str(e)}")
                
                if project_id:
                    firebase_admin.initialize_app(cred, {'projectId': project_id})
                    logger.info(f"✅ Firebase Admin SDK inicializado con credenciales de: {credential_path}, project_id: {project_id}")
                else:
                    # Intentar inicializar sin project_id explícito (Firebase debería extraerlo del JSON)
                    # Pero si falla, intentar leer el project_id del JSON nuevamente
                    try:
                        firebase_admin.initialize_app(cred)
                        # Verificar si se inicializó correctamente obteniendo el app
                        app = firebase_admin.get_app()
                        # Intentar obtener project_id del app
                        app_project_id = getattr(app, 'project_id', None)
                        if not app_project_id:
                            # Si no tiene project_id, intentar leerlo del JSON y reinicializar
                            with open(credential_path, 'r', encoding='utf-8') as f:
                                cred_data = json.load(f)
                                app_project_id = cred_data.get('project_id')
                                if app_project_id:
                                    # Reinicializar con project_id
                                    firebase_admin.delete_app(app)
                                    firebase_admin.initialize_app(cred, {'projectId': app_project_id})
                                    logger.info(f"✅ Firebase Admin SDK reinicializado con project_id: {app_project_id}")
                                else:
                                    logger.warning(f"⚠️ Firebase Admin SDK inicializado sin project_id explícito. Puede fallar al enviar notificaciones.")
                                    logger.warning(f"   El archivo JSON no contiene 'project_id'. Configura FIREBASE_PROJECT_ID")
                        else:
                            logger.info(f"✅ Firebase Admin SDK inicializado con project_id del app: {app_project_id}")
                    except Exception as init_error:
                        logger.error(f"Error inicializando Firebase: {str(init_error)}")
                        # Intentar leer project_id del JSON y reinicializar
                        try:
                            with open(credential_path, 'r', encoding='utf-8') as f:
                                cred_data = json.load(f)
                                app_project_id = cred_data.get('project_id')
                                if app_project_id:
                                    firebase_admin.initialize_app(cred, {'projectId': app_project_id})
                                    logger.info(f"✅ Firebase Admin SDK inicializado con project_id del JSON: {app_project_id}")
                                else:
                                    raise init_error
                        except Exception:
                            logger.error(f"⚠️ No se pudo inicializar Firebase Admin SDK: {str(init_error)}")
                            raise
            else:
                # Intentar usar credenciales por defecto (variable de entorno GOOGLE_APPLICATION_CREDENTIALS)
                if project_id:
                    firebase_admin.initialize_app(options={'projectId': project_id})
                    logger.info(f"Firebase Admin SDK inicializado con project_id: {project_id}")
                else:
                    # Intentar inicializar sin opciones (Firebase deber?a obtener project_id del archivo JSON)
                    firebase_admin.initialize_app()
                    logger.info("Firebase Admin SDK inicializado con credenciales por defecto")
            
            return True
        except Exception as e:
            logger.error(f"Error inicializando Firebase Admin SDK: {str(e)}")
            return False

    @staticmethod
    @BaseService.handle_service_errors
    async def registrar_token_dispositivo(
        token_fcm: str,
        codigo_trabajador: str,
        plataforma: str,
        modelo_dispositivo: Optional[str] = None,
        version_app: Optional[str] = None,
        version_so: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registra o actualiza el token FCM de un dispositivo.
        
        Args:
            token_fcm: Token de Firebase Cloud Messaging
            codigo_trabajador: Código del trabajador
            plataforma: 'A' (Android) o 'I' (iOS)
            modelo_dispositivo: Modelo del dispositivo (opcional)
            version_app: Versión de la app (opcional)
            version_so: Versión del SO (opcional)
            
        Returns:
            Dict con id_dispositivo y mensaje
        """
        try:
            # Verificar si el token ya existe
            dispositivo_existente = execute_query(
                SELECT_DISPOSITIVO_BY_TOKEN,
                (token_fcm,)
            )
            
            resultado = None
            necesita_insertar = True
            
            if dispositivo_existente and len(dispositivo_existente) > 0:
                # El token existe, intentar actualizar
                dispositivo_data = dispositivo_existente[0] if isinstance(dispositivo_existente, list) else dispositivo_existente
                dispositivo_codigo = dispositivo_data.get('codigo_trabajador') if isinstance(dispositivo_data, dict) else None
                
                # Si el dispositivo existe pero pertenece a otro trabajador, actualizar el codigo_trabajador también
                if dispositivo_codigo and dispositivo_codigo != codigo_trabajador:
                    logger.info(f"Token existe pero pertenece a otro trabajador ({dispositivo_codigo} -> {codigo_trabajador}). Actualizando codigo_trabajador...")
                
                # Intentar actualizar dispositivo existente (incluyendo codigo_trabajador)
                params_update = (
                    codigo_trabajador,  # Actualizar codigo_trabajador también
                    modelo_dispositivo,
                    version_app,
                    version_so,
                    token_fcm
                )
                resultado = execute_update(UPDATE_DISPOSITIVO_TOKEN, params_update)
                
                # Verificar que realmente se actualizó
                # En SQL Server con OUTPUT, rowcount puede ser -1 aunque el UPDATE funcionó
                # Por eso verificamos si hay id_dispositivo en el OUTPUT
                rows_affected = resultado.get('rows_affected', 0)
                id_dispositivo = resultado.get('id_dispositivo')
                
                if id_dispositivo:
                    # El UPDATE funcionó (hay OUTPUT con id_dispositivo)
                    logger.info(f"Token actualizado para dispositivo {id_dispositivo} (rows_affected: {rows_affected})")
                    return {
                        'mensaje': 'Token actualizado exitosamente',
                        'id_dispositivo': id_dispositivo
                    }
                elif rows_affected > 0:
                    # UPDATE funcionó pero no hay OUTPUT (caso raro)
                    logger.info(f"Token actualizado (rows_affected: {rows_affected}) pero sin OUTPUT")
                    # Intentar obtener el id_dispositivo consultando nuevamente
                    dispositivo_actualizado = execute_query(
                        SELECT_DISPOSITIVO_BY_TOKEN,
                        (token_fcm,)
                    )
                    if dispositivo_actualizado and len(dispositivo_actualizado) > 0:
                        dispositivo_data = dispositivo_actualizado[0] if isinstance(dispositivo_actualizado, list) else dispositivo_actualizado
                        id_dispositivo = dispositivo_data.get('id_dispositivo') if isinstance(dispositivo_data, dict) else dispositivo_data[0] if isinstance(dispositivo_data, (list, tuple)) else None
                        if id_dispositivo:
                            logger.info(f"Token actualizado para dispositivo {id_dispositivo}")
                            return {
                                'mensaje': 'Token actualizado exitosamente',
                                'id_dispositivo': id_dispositivo
                            }
                
                # UPDATE no encontró filas o no devolvió OUTPUT
                logger.warning(f"UPDATE no encontró filas o no devolvió OUTPUT (rows_affected: {rows_affected}). Intentando INSERT...")
                necesita_insertar = True
            
            # Insertar nuevo dispositivo (si no existe o si el UPDATE falló)
            if necesita_insertar:
                params_insert = (
                    codigo_trabajador,
                    token_fcm,
                    plataforma,
                    modelo_dispositivo,
                    version_app,
                    version_so
                )
                try:
                    resultado = execute_insert(INSERT_DISPOSITIVO, params_insert)
                    
                    if resultado and 'id_dispositivo' in resultado:
                        id_dispositivo = resultado['id_dispositivo']
                        logger.info(f"Token registrado para dispositivo {id_dispositivo}")
                        return {
                            'mensaje': 'Token registrado exitosamente',
                            'id_dispositivo': id_dispositivo
                        }
                    else:
                        raise ServiceError(
                            status_code=500,
                            detail="Error al registrar el token",
                            internal_code="TOKEN_REGISTER_ERROR"
                        )
                except DatabaseError as e:
                    # Si el INSERT falla por UNIQUE constraint, significa que el token existe
                    # Intentar UPDATE nuevamente (puede que haya un problema de timing)
                    error_str = str(e)
                    if 'UNIQUE KEY constraint' in error_str or 'duplicate key' in error_str.lower():
                        logger.warning(f"INSERT falló por token duplicado. Intentando UPDATE nuevamente...")
                        # Intentar UPDATE con codigo_trabajador incluido
                        params_update = (
                            codigo_trabajador,
                            modelo_dispositivo,
                            version_app,
                            version_so,
                            token_fcm
                        )
                        resultado = execute_update(UPDATE_DISPOSITIVO_TOKEN, params_update)
                        
                        # Verificar si hay id_dispositivo en el OUTPUT (el UPDATE funcionó)
                        id_dispositivo = resultado.get('id_dispositivo')
                        rows_affected = resultado.get('rows_affected', 0)
                        
                        if id_dispositivo:
                            # El UPDATE funcionó (hay OUTPUT con id_dispositivo)
                            logger.info(f"Token actualizado para dispositivo {id_dispositivo} después de fallo en INSERT (rows_affected: {rows_affected})")
                            return {
                                'mensaje': 'Token actualizado exitosamente',
                                'id_dispositivo': id_dispositivo
                            }
                        elif rows_affected > 0:
                            # UPDATE funcionó pero no hay OUTPUT, consultar nuevamente
                            dispositivo_actualizado = execute_query(
                                SELECT_DISPOSITIVO_BY_TOKEN,
                                (token_fcm,)
                            )
                            if dispositivo_actualizado and len(dispositivo_actualizado) > 0:
                                dispositivo_data = dispositivo_actualizado[0] if isinstance(dispositivo_actualizado, list) else dispositivo_actualizado
                                id_dispositivo = dispositivo_data.get('id_dispositivo') if isinstance(dispositivo_data, dict) else dispositivo_data[0] if isinstance(dispositivo_data, (list, tuple)) else None
                                if id_dispositivo:
                                    logger.info(f"Token actualizado para dispositivo {id_dispositivo} después de fallo en INSERT")
                                    return {
                                        'mensaje': 'Token actualizado exitosamente',
                                        'id_dispositivo': id_dispositivo
                                    }
                        
                        raise ServiceError(
                            status_code=500,
                            detail="Error al registrar/actualizar el token. El token existe pero no se pudo actualizar.",
                            internal_code="TOKEN_UPDATE_ERROR"
                        )
                    else:
                        # Re-lanzar el error si no es un error de UNIQUE constraint
                        raise
            else:
                raise ServiceError(
                    status_code=500,
                    detail="Error inesperado al procesar el token",
                    internal_code="TOKEN_PROCESS_ERROR"
                )
                    
        except ServiceError:
            raise
        except Exception as e:
            logger.exception(f"Error registrando token: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error al registrar token del dispositivo",
                internal_code="TOKEN_REGISTER_ERROR"
            )

    @staticmethod
    def obtener_tokens_aprobadores(codigo_area: str) -> List[str]:
        """
        Obtiene los tokens FCM de los aprobadores de un ?rea.
        
        Args:
            codigo_area: C?digo del ?rea
            
        Returns:
            Lista de tokens FCM
        """
        try:
            resultado = execute_query(
                SELECT_TOKENS_APROBADORES,
                (codigo_area,)
            )
            
            tokens = [row['token_fcm'] for row in resultado if row.get('token_fcm')]
            logger.info(
                f"Se encontraron {len(tokens)} tokens para aprobadores del ?rea {codigo_area}. "
                f"Total aprobadores encontrados: {len(resultado)}"
            )
            
            if resultado and len(tokens) == 0:
                logger.warning(
                    f"Se encontraron {len(resultado)} aprobadores pero ninguno tiene token FCM v?lido. "
                    f"C?digos: {[r.get('codigo_trabajador') for r in resultado]}"
                )
            
            return tokens
            
        except Exception as e:
            logger.exception(f"Error obteniendo tokens de aprobadores: {str(e)}")
            return []
    
    @staticmethod
    def obtener_tokens_aprobadores_por_trabajador(codigo_trabajador: str, nivel_jerarquico: Optional[int] = None) -> List[str]:
        """
        Obtiene los tokens FCM de los aprobadores seg?n la jerarqu?a del trabajador solicitante.
        Este m?todo es m?s preciso que obtener_tokens_aprobadores porque considera ?rea, secci?n y cargo.
        
        Args:
            codigo_trabajador: C?digo del trabajador que cre? la solicitud
            nivel_jerarquico: Nivel jer?rquico espec?fico a filtrar (opcional). Si es None, retorna todos los niveles.
                              Si es 1, solo retorna aprobadores del nivel 1, etc.
            
        Returns:
            Lista de tokens FCM de los aprobadores
        """
        try:
            # Primero obtener los aprobadores seg?n la jerarqu?a del trabajador
            aprobadores = execute_query(
                SELECT_APROBADORES_POR_TRABAJADOR,
                (codigo_trabajador,)
            )
            
            if not aprobadores:
                logger.warning(f"No se encontraron aprobadores para el trabajador {codigo_trabajador}")
                return []
            
            # Filtrar por nivel si se especifica
            if nivel_jerarquico is not None:
                aprobadores = [apr for apr in aprobadores if apr.get('nivel_jerarquico') == nivel_jerarquico]
                logger.info(
                    f"Filtrados aprobadores del nivel {nivel_jerarquico} para trabajador {codigo_trabajador}"
                )
            
            codigos_aprobadores = [apr['codigo_trabajador_aprobador'] for apr in aprobadores]
            logger.info(
                f"Se encontraron {len(codigos_aprobadores)} aprobadores para trabajador {codigo_trabajador} "
                f"(nivel{' ' + str(nivel_jerarquico) if nivel_jerarquico is not None else 's todos'}): {codigos_aprobadores}"
            )
            
            # Obtener tokens de esos aprobadores
            tokens = NotificacionesService.obtener_tokens_por_codigos(codigos_aprobadores)
            
            logger.info(
                f"Se obtuvieron {len(tokens)} tokens FCM de {len(codigos_aprobadores)} aprobadores para trabajador {codigo_trabajador}"
            )
            
            return tokens
            
        except Exception as e:
            logger.exception(f"Error obteniendo tokens de aprobadores por trabajador: {str(e)}")
            return []

    @staticmethod
    def obtener_tokens_por_codigos(codigos_trabajadores: List[str]) -> List[str]:
        """
        Obtiene los tokens FCM de una lista de c?digos de trabajadores.
        
        Args:
            codigos_trabajadores: Lista de c?digos de trabajadores
            
        Returns:
            Lista de tokens FCM
        """
        try:
            if not codigos_trabajadores:
                return []
            
            # Construir query con placeholders din?micos
            # SQL Server requiere que los placeholders sean expl?citos
            placeholders = ','.join(['?' for _ in codigos_trabajadores])
            query = SELECT_TOKENS_BY_CODIGOS_TRABAJADORES.format(placeholders)
            
            resultado = execute_query(query, tuple(codigos_trabajadores))
            
            tokens = [row['token_fcm'] for row in resultado if row.get('token_fcm')]
            logger.info(f"Se encontraron {len(tokens)} tokens para {len(codigos_trabajadores)} trabajadores")
            return tokens
            
        except Exception as e:
            logger.exception(f"Error obteniendo tokens por c?digos: {str(e)}")
            return []

    @staticmethod
    def enviar_notificacion_multicast(
        tokens: List[str],
        titulo: str,
        cuerpo: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Env?a una notificaci?n push a m?ltiples dispositivos usando Firebase Cloud Messaging.
        
        Args:
            tokens: Lista de tokens FCM
            titulo: T?tulo de la notificaci?n
            cuerpo: Cuerpo de la notificaci?n
            data: Datos adicionales (opcional)
            
        Returns:
            Dict con informaci?n del resultado del env?o
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK no est? disponible. No se puede enviar notificaci?n.")
            return {
                'enviado': False,
                'mensaje': 'Firebase Admin SDK no est? disponible',
                'success_count': 0,
                'failure_count': len(tokens) if tokens else 0
            }
        
        # Verificar que Firebase esté inicializado y tenga project_id
        try:
            app = firebase_admin.get_app()
            # Verificar que tenga project_id
            project_id = getattr(app, 'project_id', None)
            if not project_id:
                # Intentar obtener project_id del archivo JSON o variables de entorno
                import os
                import json
                
                firebase_cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                firebase_project_id = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
                
                if not firebase_project_id and firebase_cred_path and os.path.exists(firebase_cred_path):
                    try:
                        with open(firebase_cred_path, 'r', encoding='utf-8') as f:
                            cred_data = json.load(f)
                            firebase_project_id = cred_data.get('project_id')
                    except Exception as e:
                        logger.warning(f"No se pudo leer project_id del JSON: {str(e)}")
                
                if firebase_project_id:
                    # Reinicializar Firebase con project_id
                    logger.warning(f"Firebase no tiene project_id. Reinicializando con project_id: {firebase_project_id}")
                    try:
                        firebase_admin.delete_app(app)
                        if firebase_cred_path and os.path.exists(firebase_cred_path):
                            cred = credentials.Certificate(firebase_cred_path)
                            firebase_admin.initialize_app(cred, {'projectId': firebase_project_id})
                        else:
                            firebase_admin.initialize_app(options={'projectId': firebase_project_id})
                        logger.info(f"✅ Firebase Admin SDK reinicializado con project_id: {firebase_project_id}")
                    except Exception as e:
                        logger.error(f"Error reinicializando Firebase: {str(e)}")
                        return {
                            'enviado': False,
                            'mensaje': f'Firebase Admin SDK no tiene project_id y no se pudo reinicializar: {str(e)}',
                            'success_count': 0,
                            'failure_count': len(tokens) if tokens else 0
                        }
                else:
                    logger.error("Firebase Admin SDK no tiene project_id y no se pudo obtener de variables de entorno o archivo JSON.")
                    return {
                        'enviado': False,
                        'mensaje': 'Firebase Admin SDK no tiene project_id. Configura FIREBASE_PROJECT_ID o asegúrate de que el archivo JSON contenga "project_id".',
                        'success_count': 0,
                        'failure_count': len(tokens) if tokens else 0
                    }
        except ValueError:
            logger.error("Firebase Admin SDK no está inicializado. No se puede enviar notificación.")
            logger.error("Configura FIREBASE_CREDENTIALS_PATH o GOOGLE_APPLICATION_CREDENTIALS con el archivo JSON de credenciales.")
            logger.error("El archivo JSON debe contener 'project_id' o configura FIREBASE_PROJECT_ID como variable de entorno.")
            return {
                'enviado': False,
                'mensaje': 'Firebase Admin SDK no está inicializado. Configura las credenciales de Firebase.',
                'success_count': 0,
                'failure_count': len(tokens) if tokens else 0
            }
        
        if not tokens:
            logger.warning("No hay tokens para enviar notificación")
            return {
                'enviado': False,
                'mensaje': 'No hay tokens disponibles',
                'success_count': 0,
                'failure_count': 0
            }
        
        try:
            # Preparar datos
            data_dict = data or {}
            # Asegurar que todos los valores en data sean strings
            data_dict = {k: str(v) for k, v in data_dict.items()}
            
            # Crear mensaje multicast
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo
                ),
                data=data_dict,
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='fidesoft_channel',
                        sound='default'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1
                        )
                    )
                )
            )
            
            # Enviar notificaci?n usando send_each_for_multicast (m?todo correcto en v7.0.0+)
            # send_multicast() fue deprecado en v7.0.0
            response = messaging.send_each_for_multicast(message)
            
            logger.info(
                f"Notificaciones enviadas: {response.success_count}/{len(tokens)} exitosas, "
                f"{response.failure_count} fallidas"
            )
            
            # Manejar tokens inv?lidos
            if response.failure_count > 0:
                invalid_tokens = []
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        if resp.exception:
                            error_code = resp.exception.code
                            error_message = str(resp.exception)
                            logger.warning(
                                f"Error enviando notificaci?n a token {idx}: {error_code} - {error_message}"
                            )
                            # C?digos que indican token inv?lido
                            if error_code in ['INVALID_ARGUMENT', 'UNREGISTERED', 'NOT_FOUND']:
                                invalid_tokens.append(tokens[idx])
                
                if invalid_tokens:
                    logger.warning(f"Se encontraron {len(invalid_tokens)} tokens inv?lidos que deber?an marcarse como inactivos")
                    # TODO: Marcar tokens como inactivos en la BD
            
            return {
                'enviado': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'total_tokens': len(tokens)
            }
            
        except Exception as e:
            logger.exception(f"Error enviando notificaci?n multicast: {str(e)}")
            return {
                'enviado': False,
                'mensaje': str(e),
                'success_count': 0,
                'failure_count': len(tokens) if tokens else 0
            }

    @staticmethod
    async def enviar_notificacion_nueva_solicitud(
        id_solicitud: int,
        tipo_solicitud: str,
        codigo_trabajador: str,
        nombre_trabajador: str,
        codigo_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Env?a notificaci?n push cuando se crea una nueva solicitud.
        
        Args:
            id_solicitud: ID de la solicitud creada
            tipo_solicitud: 'V' (vacaciones) o 'P' (permiso)
            codigo_trabajador: C?digo del trabajador que cre? la solicitud
            nombre_trabajador: Nombre del trabajador
            codigo_area: C?digo del ?rea del trabajador (opcional, se obtiene si no se proporciona)
            
        Returns:
            Dict con informaci?n del resultado del env?o
        """
        try:
            # Si no se proporciona c?digo de ?rea, obtenerlo del trabajador
            if not codigo_area:
                area_result = execute_query(
                    SELECT_AREA_TRABAJADOR,
                    (codigo_trabajador,)
                )
                if area_result and area_result[0].get('codigo_area'):
                    codigo_area = area_result[0]['codigo_area']
                else:
                    logger.warning(f"No se pudo obtener c?digo de ?rea para trabajador {codigo_trabajador}")
                    return {
                        'enviado': False,
                        'mensaje': 'No se pudo determinar el ?rea del trabajador',
                        'success_count': 0,
                        'failure_count': 0
                    }
            
            # Obtener tokens de aprobadores del NIVEL 1 solamente (flujo jer?rquico)
            # Solo el nivel 1 debe recibir notificaci?n cuando se crea la solicitud
            # Los siguientes niveles recibir?n notificaci?n cuando el nivel anterior apruebe
            tokens = NotificacionesService.obtener_tokens_aprobadores_por_trabajador(
                codigo_trabajador, 
                nivel_jerarquico=1  # Solo nivel 1
            )
            
            # Si no hay tokens con el m?todo preciso, intentar con el m?todo por ?rea (solo nivel 1)
            if not tokens:
                logger.info(f"No se encontraron tokens del nivel 1 con m?todo preciso, intentando por ?rea {codigo_area}")
                # Obtener tokens por ?rea pero filtrar solo nivel 1
                tokens_area = NotificacionesService.obtener_tokens_aprobadores(codigo_area)
                # Filtrar solo nivel 1 (necesitamos obtener los aprobadores del nivel 1 primero)
                if tokens_area:
                    # Obtener aprobadores del nivel 1 para filtrar tokens
                    aprobadores_nivel1 = execute_query(
                        SELECT_APROBADORES_POR_TRABAJADOR,
                        (codigo_trabajador,)
                    )
                    if aprobadores_nivel1:
                        codigos_nivel1 = [
                            apr['codigo_trabajador_aprobador'] 
                            for apr in aprobadores_nivel1 
                            if apr.get('nivel_jerarquico') == 1
                        ]
                        # Obtener tokens solo de los aprobadores del nivel 1
                        tokens = NotificacionesService.obtener_tokens_por_codigos(codigos_nivel1)
            
            if not tokens:
                logger.warning(
                    f"No hay tokens de aprobadores para trabajador {codigo_trabajador} (?rea: {codigo_area}). "
                    f"Verificar que existan aprobadores en ppavac_jerarquia y tokens en ppavac_dispositivo."
                )
                return {
                    'enviado': False,
                    'mensaje': 'No hay aprobadores con tokens registrados',
                    'success_count': 0,
                    'failure_count': 0
                }
            
            logger.info(f"Se enviar?n notificaciones a {len(tokens)} dispositivos para solicitud {id_solicitud}")
            
            # Preparar mensaje
            tipo_texto = 'vacaciones' if tipo_solicitud == 'V' else 'permiso'
            titulo = "Nueva solicitud pendiente"
            cuerpo = f"Solicitud de {tipo_texto} de {nombre_trabajador}"
            
            # Preparar datos
            data = {
                'tipo_solicitud': tipo_solicitud,
                'id_solicitud': str(id_solicitud),
                'codigo_trabajador': codigo_trabajador,
                'tipo': 'nueva_solicitud'
            }
            
            # Enviar notificaci?n
            logger.info(
                f"Enviando notificaci?n push para solicitud {id_solicitud}: "
                f"tipo={tipo_solicitud}, trabajador={codigo_trabajador}, tokens={len(tokens)}"
            )
            
            resultado = NotificacionesService.enviar_notificacion_multicast(
                tokens=tokens,
                titulo=titulo,
                cuerpo=cuerpo,
                data=data
            )
            
            if resultado.get('enviado'):
                logger.info(
                    f"? Notificaci?n de nueva solicitud {id_solicitud} enviada exitosamente: "
                    f"{resultado.get('success_count', 0)}/{len(tokens)} dispositivos"
                )
            else:
                logger.error(
                    f"? Error enviando notificaci?n para solicitud {id_solicitud}: "
                    f"{resultado.get('mensaje', 'Error desconocido')}"
                )
            
            return resultado
            
        except Exception as e:
            logger.exception(f"Error enviando notificaci?n de nueva solicitud: {str(e)}")
            return {
                'enviado': False,
                'mensaje': str(e),
                'success_count': 0,
                'failure_count': 0
            }
    
    @staticmethod
    async def enviar_notificacion_siguiente_nivel(
        id_solicitud: int,
        codigo_trabajador_solicitante: str,
        nombre_trabajador_solicitante: str,
        nivel_siguiente: int,
        codigo_trabajador_aprobador_siguiente: str,
        tipo_solicitud: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Env?a notificaci?n push al siguiente nivel cuando un nivel aprueba.
        
        Args:
            id_solicitud: ID de la solicitud
            codigo_trabajador_solicitante: C?digo del trabajador que cre? la solicitud
            nombre_trabajador_solicitante: Nombre del trabajador solicitante
            nivel_siguiente: Nivel jer?rquico siguiente (ej: 2, 3, etc.)
            codigo_trabajador_aprobador_siguiente: C?digo del trabajador aprobador del siguiente nivel
            
        Returns:
            Dict con informaci?n del resultado del env?o
        """
        try:
            logger.info(
                f"Enviando notificaci?n push al nivel {nivel_siguiente} "
                f"(aprobador: {codigo_trabajador_aprobador_siguiente}) para solicitud {id_solicitud}"
            )
            
            # Obtener tokens del aprobador del siguiente nivel
            tokens = NotificacionesService.obtener_tokens_por_codigos([codigo_trabajador_aprobador_siguiente])
            
            if not tokens:
                logger.warning(
                    f"No hay tokens registrados para el aprobador del nivel {nivel_siguiente} "
                    f"({codigo_trabajador_aprobador_siguiente})"
                )
                return {
                    'enviado': False,
                    'mensaje': f'No hay tokens registrados para el aprobador del nivel {nivel_siguiente}',
                    'success_count': 0,
                    'failure_count': 0
                }
            
            # Obtener tipo de solicitud si no se proporciona
            if not tipo_solicitud:
                from app.db.queries import SELECT_SOLICITUD_BY_ID
                solicitud_result = execute_query(SELECT_SOLICITUD_BY_ID, (id_solicitud,))
                if solicitud_result:
                    tipo_solicitud = solicitud_result[0].get('tipo_solicitud', 'V')
                else:
                    tipo_solicitud = 'V'  # Default a vacaciones
            
            # Preparar mensaje
            tipo_texto = 'vacaciones' if tipo_solicitud == 'V' else 'permiso'
            titulo = "Solicitud pendiente de aprobación"
            cuerpo = f"Solicitud de {tipo_texto} de {nombre_trabajador_solicitante} requiere su aprobación (Nivel {nivel_siguiente})"
            
            # Preparar datos
            data = {
                'tipo_solicitud': tipo_solicitud,
                'id_solicitud': str(id_solicitud),
                'codigo_trabajador': codigo_trabajador_solicitante,
                'tipo': 'siguiente_nivel',
                'nivel': str(nivel_siguiente)
            }
            
            # Enviar notificaci?n
            logger.info(
                f"Enviando notificaci?n push al nivel {nivel_siguiente} para solicitud {id_solicitud}: "
                f"tokens={len(tokens)}"
            )
            
            resultado = NotificacionesService.enviar_notificacion_multicast(
                tokens=tokens,
                titulo=titulo,
                cuerpo=cuerpo,
                data=data
            )
            
            if resultado.get('enviado'):
                logger.info(
                    f"✅ Notificaci?n al nivel {nivel_siguiente} para solicitud {id_solicitud} enviada exitosamente: "
                    f"{resultado.get('success_count', 0)}/{len(tokens)} dispositivos"
                )
            else:
                logger.error(
                    f"❌ Error enviando notificaci?n al nivel {nivel_siguiente} para solicitud {id_solicitud}: "
                    f"{resultado.get('mensaje', 'Error desconocido')}"
                )
            
            return resultado
            
        except Exception as e:
            logger.exception(f"Error enviando notificaci?n al siguiente nivel: {str(e)}")
            return {
                'enviado': False,
                'mensaje': str(e),
                'success_count': 0,
                'failure_count': 0
            }
