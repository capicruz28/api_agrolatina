from typing import Any, Dict, Optional
import logging

from app.core.exceptions import NotFoundError, ServiceError, DatabaseError
from app.services.base_service import BaseService

from app.db.queries import (
    execute_query,
    execute_update,
    SELECT_AVISO_AP_PENDIENTE,
    UPDATE_AVISO_AP_VISUALIZADO,
    UPDATE_AVISO_AP_ACEPTADO,
)

logger = logging.getLogger(__name__)


class AvisoApService(BaseService):
    """
    Servicio para el aviso general de aceptación (ctpref='AP') en pbolet00.

    Flujo:
    - Consultar aviso pendiente (saprob='N') y entregar PDF.
    - Marcar visualización (fvisual) al abrir/visualizar el PDF.
    - Aceptar (faprob + saprob='S') cuando el usuario marque Conforme y grabe.
    """

    @staticmethod
    def _archivo_a_base64(archivo_hex) -> str:
        """Convierte bytes o hex-string a base64 (mismo patrón que VacacionesPermisosService)."""
        import base64

        if isinstance(archivo_hex, bytes):
            pdf_bytes = archivo_hex
        elif isinstance(archivo_hex, str):
            hex_string = archivo_hex
            if hex_string.startswith("0x") or hex_string.startswith("0X"):
                hex_string = hex_string[2:]
            pdf_bytes = bytes.fromhex(hex_string)
        else:
            raise ValueError(f"Tipo de dato no soportado para archivo: {type(archivo_hex)}")

        return base64.b64encode(pdf_bytes).decode("utf-8")

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_aviso_pendiente(codigo_trabajador: str) -> Dict[str, Any]:
        """
        Devuelve el aviso AP pendiente para el trabajador.
        Si no existe, retorna pendiente=False.
        """
        try:
            resultado = execute_query(SELECT_AVISO_AP_PENDIENTE, (codigo_trabajador,))
            if not resultado:
                return {"pendiente": False, "aviso": None}

            row = resultado[0]
            archivo_hex = row.get("archivo_pdf_hex")
            if not archivo_hex:
                raise NotFoundError(
                    detail="El aviso pendiente no tiene archivo PDF asociado. Contacte al administrador.",
                    internal_code="AVISO_AP_SIN_ARCHIVO",
                )

            try:
                pdf_base64 = AvisoApService._archivo_a_base64(archivo_hex)
            except Exception as e:
                logger.error(f"Error convirtiendo aviso AP a base64: {str(e)}")
                raise ServiceError(
                    status_code=500,
                    detail="Error al procesar el archivo PDF del aviso",
                    internal_code="AVISO_AP_CONVERSION_ERROR",
                )

            nombre_archivo = f"aviso_ap_{codigo_trabajador}.pdf"
            aviso = {
                "ctraba": row.get("ctraba"),
                "saprob": row.get("saprob"),
                "faprob": row.get("faprob"),
                "fvisual": row.get("fvisual"),
                "archivo_pdf_base64": pdf_base64,
                "nombre_archivo": nombre_archivo,
            }

            return {"pendiente": True, "aviso": aviso}

        except (NotFoundError, ServiceError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD obteniendo aviso AP: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener el aviso",
                internal_code="AVISO_AP_DB_ERROR",
            )
        except Exception as e:
            logger.exception(f"Error inesperado obteniendo aviso AP: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener el aviso",
                internal_code="AVISO_AP_UNEXPECTED_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def marcar_visualizado(codigo_trabajador: str) -> Dict[str, Any]:
        """
        Actualiza fvisual = ahora, si está NULL y el aviso sigue pendiente.
        Es idempotente: si ya estaba visualizado, no modifica (rows_affected = 0).
        """
        try:
            result = execute_update(UPDATE_AVISO_AP_VISUALIZADO, (codigo_trabajador,))
            return {
                "rows_affected": result.get("rows_affected", 0),
                "fvisual": result.get("fvisual"),
            }
        except DatabaseError as db_err:
            logger.error(f"Error de BD marcando visualizado aviso AP: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al actualizar visualización del aviso",
                internal_code="AVISO_AP_VISUALIZADO_DB_ERROR",
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def aceptar_aviso(codigo_trabajador: str) -> Dict[str, Any]:
        """
        Acepta el aviso: faprob = ahora y saprob = 'S' si estaba pendiente.
        """
        try:
            result = execute_update(UPDATE_AVISO_AP_ACEPTADO, (codigo_trabajador,))
            return {
                "rows_affected": result.get("rows_affected", 0),
                "faprob": result.get("faprob"),
                "saprob": result.get("saprob"),
            }
        except DatabaseError as db_err:
            logger.error(f"Error de BD aceptando aviso AP: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al aceptar el aviso",
                internal_code="AVISO_AP_ACEPTAR_DB_ERROR",
            )

