from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

import pyodbc

from app.core.exceptions import DatabaseError, ServiceError, ValidationError
from app.core.logging_config import get_logger
from app.db.cartera_db import execute_sp_api_agrolatina_cartera_nuevo

logger = get_logger(__name__)


class EstRegContablePagosService:
    PROCEDURE_NAME = "dbo.sp_api_agrolatina_cartera_nuevo"

    @staticmethod
    def _build_params(
        *,
        anio: Optional[int] = None,
        mes: Optional[int] = None,
        campana: Optional[str] = None,
        tipo_documento: Optional[str] = None,
        fecha: Optional[date] = None,
    ) -> Dict[str, Any]:
        if anio is not None and (anio < 1900 or anio > 2100):
            raise ValidationError("anio fuera de rango (1900-2100)", internal_code="INVALID_ANIO")

        if mes is not None and (mes < 1 or mes > 12):
            raise ValidationError("mes fuera de rango (1-12)", internal_code="INVALID_MES")

        if campana is not None:
            campana = campana.strip()
            if not campana:
                campana = None
            elif len(campana) > 7:
                raise ValidationError("campana debe tener max 7 caracteres", internal_code="INVALID_CAMPANA")

        if tipo_documento is not None:
            tipo_documento = tipo_documento.strip()
            if not tipo_documento:
                tipo_documento = None
            elif len(tipo_documento) > 2:
                raise ValidationError("tipo_documento debe tener max 2 caracteres", internal_code="INVALID_TIPO_DOC")

        # El SP nuevo ya define @wcempre internamente (actualmente 'A').
        # Solo enviamos los parámetros expuestos por el SP.
        params: Dict[str, Any] = {}
        if anio is not None:
            params["wcannos"] = f"{anio:04d}"
        if mes is not None:
            params["wcmeses"] = f"{mes:02d}"
        if campana is not None:
            params["wccampa"] = campana
        if tipo_documento is not None:
            params["wctpdoc"] = tipo_documento
        if fecha is not None:
            params["wfecha"] = fecha

        return params

    @staticmethod
    def _listar_sync(
        *,
        anio: Optional[int] = None,
        mes: Optional[int] = None,
        campana: Optional[str] = None,
        tipo_documento: Optional[str] = None,
        fecha: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        params = EstRegContablePagosService._build_params(
            anio=anio,
            mes=mes,
            campana=campana,
            tipo_documento=tipo_documento,
            fecha=fecha,
        )
        logger.debug(
            "Consultando estregcontablepagos (pool + fetchmany)",
            extra={"procedure": EstRegContablePagosService.PROCEDURE_NAME, "param_keys": list(params.keys())},
        )
        try:
            return execute_sp_api_agrolatina_cartera_nuevo(params)
        except pyodbc.Error as e:
            logger.error(f"pyodbc en cartera: {str(e)}")
            raise DatabaseError(detail=f"Error en el procedimiento: {str(e)}")

    @staticmethod
    async def listar(
        *,
        anio: Optional[int] = None,
        mes: Optional[int] = None,
        campana: Optional[str] = None,
        tipo_documento: Optional[str] = None,
        fecha: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta `sp_api_agrolatina_cartera_new` con filtros opcionales.
        La lectura BD corre en un hilo (no bloquea el event loop de FastAPI).
        """
        try:
            return await asyncio.to_thread(
                EstRegContablePagosService._listar_sync,
                anio=anio,
                mes=mes,
                campana=campana,
                tipo_documento=tipo_documento,
                fecha=fecha,
            )
        except (ValidationError, ServiceError):
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.exception(f"Error inesperado consultando estregcontablepagos: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno consultando cartera",
                internal_code="ESTREGCONTABLEPAGOS_ERROR",
            )
