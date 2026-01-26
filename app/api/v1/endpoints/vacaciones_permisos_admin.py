# app/api/v1/endpoints/vacaciones_permisos_admin.py
"""
Endpoints administrativos para el Sistema de Gestión de Vacaciones y Permisos.

Este módulo proporciona endpoints específicos para la administración web (React),
requiriendo permisos de SuperAdministrador.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, List, Dict, Any
from datetime import date

# Schemas
from app.schemas.vacaciones_permisos import (
    SolicitudRead, SolicitudReadFull, PaginatedSolicitudResponse,
    ConfigFlujoRead, ConfigFlujoCreate,
    JerarquiaRead, JerarquiaCreate,
    SustitutoRead, SustitutoCreate,
    SaldoVacacionesRead, EstadisticasResponse
)

# Servicios
from app.services.vacaciones_permisos_service import VacacionesPermisosService

# Dependencias
from app.api.deps import get_current_active_user, RoleChecker
from app.schemas.usuario import UsuarioReadWithRoles

# Logging
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Dependencia para requerir rol de SuperAdministrador
require_superadmin = RoleChecker(["SuperAdministrador"])


# ============================================
# ENDPOINTS DE GESTIÓN DE SOLICITUDES (ADMIN)
# ============================================

@router.get(
    "/solicitudes",
    response_model=PaginatedSolicitudResponse,
    summary="Listar todas las solicitudes (SuperAdmin)",
    description="Obtiene todas las solicitudes con filtros y paginación",
    dependencies=[Depends(require_superadmin)]
)
async def listar_solicitudes_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    codigo_trabajador: Optional[str] = Query(None, description="Filtrar por trabajador"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (P, A, R, N)"),
    tipo_solicitud: Optional[str] = Query(None, description="Filtrar por tipo (V, P)"),
    fecha_desde: Optional[date] = Query(None, description="Fecha inicio del rango"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin del rango"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Lista todas las solicitudes con filtros administrativos"""
    try:
        resultado = await VacacionesPermisosService.listar_solicitudes(
            codigo_trabajador=codigo_trabajador,
            estado=estado,
            tipo_solicitud=tipo_solicitud,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            page=page,
            limit=limit
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error listando solicitudes admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar solicitudes"
        )


@router.get(
    "/solicitud/{id_solicitud}",
    response_model=SolicitudReadFull,
    summary="Obtener detalle completo de solicitud (SuperAdmin)",
    description="Obtiene el detalle completo de una solicitud con todas sus aprobaciones",
    dependencies=[Depends(require_superadmin)]
)
async def obtener_solicitud_admin(
    id_solicitud: int,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Obtiene el detalle completo de una solicitud"""
    try:
        solicitud = await VacacionesPermisosService.obtener_solicitud(id_solicitud)
        return solicitud
        
    except Exception as e:
        logger.exception(f"Error obteniendo solicitud admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener solicitud"
        )


@router.post(
    "/solicitud/{id_solicitud}/anular",
    response_model=SolicitudReadFull,
    summary="Anular solicitud (SuperAdmin)",
    description="Anula una solicitud (solo administradores)",
    dependencies=[Depends(require_superadmin)]
)
async def anular_solicitud_admin(
    id_solicitud: int,
    motivo_anulacion: str = Query(..., description="Motivo de la anulación"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Anula una solicitud (solo admin)"""
    try:
        resultado = await VacacionesPermisosService.anular_solicitud(
            id_solicitud=id_solicitud,
            motivo_anulacion=motivo_anulacion,
            usuario_anulacion=current_user.nombre_usuario
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error anulando solicitud admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al anular solicitud"
        )


# ============================================
# ENDPOINTS DE CONFIGURACIÓN DE FLUJO
# ============================================

@router.get(
    "/config-flujo",
    response_model=List[ConfigFlujoRead],
    summary="Listar configuraciones de flujo",
    description="Obtiene todas las configuraciones de flujo de aprobación",
    dependencies=[Depends(require_superadmin)]
)
async def listar_config_flujo(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Lista todas las configuraciones de flujo"""
    try:
        configs = await VacacionesPermisosService.listar_config_flujo()
        return configs
        
    except Exception as e:
        logger.exception(f"Error listando configuraciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar configuraciones de flujo"
        )


@router.post(
    "/config-flujo",
    response_model=ConfigFlujoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear configuración de flujo",
    description="Crea una nueva configuración de flujo de aprobación",
    dependencies=[Depends(require_superadmin)]
)
async def crear_config_flujo(
    config_data: ConfigFlujoCreate,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Crea una nueva configuración de flujo"""
    try:
        resultado = await VacacionesPermisosService.crear_config_flujo(
            config_data=config_data.dict(),
            usuario_registro=current_user.nombre_usuario
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error creando configuración: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear configuración de flujo"
        )


@router.get(
    "/config-flujo/{id_config}",
    response_model=ConfigFlujoRead,
    summary="Obtener configuración de flujo",
    description="Obtiene una configuración de flujo por ID",
    dependencies=[Depends(require_superadmin)]
)
async def obtener_config_flujo(
    id_config: int,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Obtiene una configuración de flujo por ID"""
    try:
        resultado = await VacacionesPermisosService.obtener_config_flujo(id_config)
        return resultado
        
    except Exception as e:
        logger.exception(f"Error obteniendo configuración: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener configuración de flujo"
        )


@router.put(
    "/config-flujo/{id_config}",
    response_model=ConfigFlujoRead,
    summary="Actualizar configuración de flujo",
    description="Actualiza una configuración de flujo existente",
    dependencies=[Depends(require_superadmin)]
)
async def actualizar_config_flujo(
    id_config: int,
    config_data: ConfigFlujoCreate,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Actualiza una configuración de flujo"""
    try:
        resultado = await VacacionesPermisosService.actualizar_config_flujo(
            id_config=id_config,
            config_data=config_data.dict(),
            usuario_modificacion=current_user.nombre_usuario
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error actualizando configuración: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar configuración de flujo"
        )


@router.delete(
    "/config-flujo/{id_config}",
    summary="Eliminar configuración de flujo",
    description="Elimina una configuración de flujo",
    dependencies=[Depends(require_superadmin)]
)
async def eliminar_config_flujo(
    id_config: int,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Elimina una configuración de flujo"""
    try:
        resultado = await VacacionesPermisosService.eliminar_config_flujo(id_config)
        return resultado
        
    except Exception as e:
        logger.exception(f"Error eliminando configuración: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar configuración de flujo"
        )


# ============================================
# ENDPOINTS DE JERARQUÍA
# ============================================

@router.get(
    "/jerarquia",
    response_model=List[JerarquiaRead],
    summary="Listar jerarquías",
    description="Obtiene todas las jerarquías de aprobación",
    dependencies=[Depends(require_superadmin)]
)
async def listar_jerarquia(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Lista todas las jerarquías"""
    try:
        jerarquias = await VacacionesPermisosService.listar_jerarquia()
        return jerarquias
        
    except Exception as e:
        logger.exception(f"Error listando jerarquías: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar jerarquías"
        )


@router.get(
    "/jerarquia/{id_jerarquia}",
    response_model=JerarquiaRead,
    summary="Obtener jerarquía",
    description="Obtiene una jerarquía por ID",
    dependencies=[Depends(require_superadmin)]
)
async def obtener_jerarquia(
    id_jerarquia: int,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Obtiene una jerarquía por ID"""
    try:
        resultado = await VacacionesPermisosService.obtener_jerarquia(id_jerarquia)
        return resultado
        
    except Exception as e:
        logger.exception(f"Error obteniendo jerarquía: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener jerarquía"
        )


@router.post(
    "/jerarquia",
    response_model=JerarquiaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear jerarquía",
    description="Crea una nueva jerarquía de aprobación",
    dependencies=[Depends(require_superadmin)]
)
async def crear_jerarquia(
    jerarquia_data: JerarquiaCreate,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Crea una nueva jerarquía"""
    try:
        resultado = await VacacionesPermisosService.crear_jerarquia(
            jerarquia_data=jerarquia_data.dict(),
            usuario_registro=current_user.nombre_usuario
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error creando jerarquía: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear jerarquía"
        )


@router.put(
    "/jerarquia/{id_jerarquia}",
    response_model=JerarquiaRead,
    summary="Actualizar jerarquía",
    description="Actualiza una jerarquía existente",
    dependencies=[Depends(require_superadmin)]
)
async def actualizar_jerarquia(
    id_jerarquia: int,
    jerarquia_data: JerarquiaCreate,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Actualiza una jerarquía"""
    try:
        resultado = await VacacionesPermisosService.actualizar_jerarquia(
            id_jerarquia=id_jerarquia,
            jerarquia_data=jerarquia_data.dict(),
            usuario_modificacion=current_user.nombre_usuario
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error actualizando jerarquía: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar jerarquía"
        )


@router.delete(
    "/jerarquia/{id_jerarquia}",
    summary="Eliminar jerarquía",
    description="Elimina una jerarquía",
    dependencies=[Depends(require_superadmin)]
)
async def eliminar_jerarquia(
    id_jerarquia: int,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Elimina una jerarquía"""
    try:
        resultado = await VacacionesPermisosService.eliminar_jerarquia(id_jerarquia)
        return resultado
        
    except Exception as e:
        logger.exception(f"Error eliminando jerarquía: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar jerarquía"
        )


# ============================================
# ENDPOINTS DE SUSTITUTOS
# ============================================

@router.get(
    "/sustitutos",
    response_model=List[SustitutoRead],
    summary="Listar sustitutos",
    description="Obtiene todos los sustitutos temporales",
    dependencies=[Depends(require_superadmin)]
)
async def listar_sustitutos(
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Lista todos los sustitutos"""
    try:
        sustitutos = await VacacionesPermisosService.listar_sustitutos()
        return sustitutos
        
    except Exception as e:
        logger.exception(f"Error listando sustitutos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar sustitutos"
        )


@router.post(
    "/sustituto",
    response_model=SustitutoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear sustituto",
    description="Crea un nuevo sustituto temporal",
    dependencies=[Depends(require_superadmin)]
)
async def crear_sustituto(
    sustituto_data: SustitutoCreate,
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Crea un nuevo sustituto"""
    try:
        resultado = await VacacionesPermisosService.crear_sustituto(
            sustituto_data=sustituto_data.dict(),
            usuario_registro=current_user.nombre_usuario
        )
        
        return resultado
        
    except Exception as e:
        logger.exception(f"Error creando sustituto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear sustituto"
        )


# ============================================
# ENDPOINTS DE REPORTES Y ESTADÍSTICAS
# ============================================

@router.get(
    "/estadisticas",
    response_model=EstadisticasResponse,
    summary="Obtener estadísticas",
    description="Obtiene estadísticas del sistema de vacaciones y permisos",
    dependencies=[Depends(require_superadmin)]
)
async def obtener_estadisticas(
    fecha_desde: Optional[date] = Query(None, description="Fecha inicio del rango"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin del rango"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Obtiene estadísticas del sistema"""
    try:
        estadisticas = await VacacionesPermisosService.obtener_estadisticas(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        return estadisticas
        
    except Exception as e:
        logger.exception(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )


@router.get(
    "/saldos",
    response_model=List[SaldoVacacionesRead],
    summary="Listar saldos de vacaciones",
    description="Obtiene los saldos de vacaciones de todos los trabajadores",
    dependencies=[Depends(require_superadmin)]
)
async def listar_saldos_vacaciones(
    codigo_area: Optional[str] = Query(None, description="Filtrar por área"),
    codigo_seccion: Optional[str] = Query(None, description="Filtrar por sección"),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Lista los saldos de vacaciones de todos los trabajadores"""
    try:
        saldos = await VacacionesPermisosService.listar_saldos_vacaciones(
            codigo_area=codigo_area,
            codigo_seccion=codigo_seccion
        )
        
        return saldos
        
    except Exception as e:
        logger.exception(f"Error listando saldos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar saldos de vacaciones"
        )


# ============================================
# ENDPOINTS DE BÚSQUEDA DE CATÁLOGOS
# ============================================

@router.get(
    "/buscar/areas",
    response_model=Dict,
    summary="Buscar áreas",
    description="Busca áreas por código o descripción con paginación",
    dependencies=[Depends(require_superadmin)]
)
async def buscar_areas(
    codigo: Optional[str] = Query(None, description="Buscar por código de área"),
    descripcion: Optional[str] = Query(None, description="Buscar por descripción"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Busca áreas con filtros"""
    try:
        resultado = await VacacionesPermisosService.buscar_areas(
            codigo=codigo,
            descripcion=descripcion,
            page=page,
            limit=limit
        )
        return resultado
    except Exception as e:
        logger.exception(f"Error buscando áreas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar áreas"
        )


@router.get(
    "/buscar/secciones",
    response_model=Dict,
    summary="Buscar secciones",
    description="Busca secciones por código o descripción con paginación",
    dependencies=[Depends(require_superadmin)]
)
async def buscar_secciones(
    codigo: Optional[str] = Query(None, description="Buscar por código de sección"),
    descripcion: Optional[str] = Query(None, description="Buscar por descripción"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Busca secciones con filtros"""
    try:
        resultado = await VacacionesPermisosService.buscar_secciones(
            codigo=codigo,
            descripcion=descripcion,
            page=page,
            limit=limit
        )
        return resultado
    except Exception as e:
        logger.exception(f"Error buscando secciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar secciones"
        )


@router.get(
    "/buscar/cargos",
    response_model=Dict,
    summary="Buscar cargos",
    description="Busca cargos por código o descripción con paginación",
    dependencies=[Depends(require_superadmin)]
)
async def buscar_cargos(
    codigo: Optional[str] = Query(None, description="Buscar por código de cargo"),
    descripcion: Optional[str] = Query(None, description="Buscar por descripción"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Busca cargos con filtros"""
    try:
        resultado = await VacacionesPermisosService.buscar_cargos(
            codigo=codigo,
            descripcion=descripcion,
            page=page,
            limit=limit
        )
        return resultado
    except Exception as e:
        logger.exception(f"Error buscando cargos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar cargos"
        )


@router.get(
    "/buscar/trabajadores",
    response_model=Dict,
    summary="Buscar trabajadores",
    description="Busca trabajadores con múltiples filtros y paginación",
    dependencies=[Depends(require_superadmin)]
)
async def buscar_trabajadores(
    codigo: Optional[str] = Query(None, description="Buscar por código de trabajador"),
    nombre: Optional[str] = Query(None, description="Buscar por nombre completo"),
    codigo_area: Optional[str] = Query(None, description="Filtrar por código de área"),
    codigo_seccion: Optional[str] = Query(None, description="Filtrar por código de sección"),
    codigo_cargo: Optional[str] = Query(None, description="Filtrar por código de cargo"),
    numero_dni: Optional[str] = Query(None, description="Buscar por número de DNI"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: UsuarioReadWithRoles = Depends(get_current_active_user)
):
    """Busca trabajadores con filtros"""
    try:
        resultado = await VacacionesPermisosService.buscar_trabajadores(
            codigo=codigo,
            nombre=nombre,
            codigo_area=codigo_area,
            codigo_seccion=codigo_seccion,
            codigo_cargo=codigo_cargo,
            numero_dni=numero_dni,
            page=page,
            limit=limit
        )
        return resultado
    except Exception as e:
        logger.exception(f"Error buscando trabajadores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar trabajadores"
        )
