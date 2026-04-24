from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import TypeAdapter

from app.core.exceptions import CustomException, ValidationError
from app.core.logging_config import get_logger
from app.schemas.estregcontablepagos import (
    EstRegContablePagosApiResponse,
    EstRegContablePagosItem,
)
from app.services.estregcontablepagos_service import EstRegContablePagosService

logger = get_logger(__name__)
router = APIRouter()

_CARTERA_ROWS = TypeAdapter(list[EstRegContablePagosItem])


def _to_api_response(raw_rows: List[dict[str, Any]]) -> EstRegContablePagosApiResponse:
    results = _CARTERA_ROWS.validate_python(raw_rows)
    return EstRegContablePagosApiResponse(
        error=0,
        total=len(results),
        mensaje="Datos Obtenidos Correctamente",
        status="ok",
        results=results,
    )


@router.get(
    "/estregcontablepagos",
    response_model=EstRegContablePagosApiResponse,
    summary="Listado completo (sin filtros)",
    description="Devuelve toda la cartera (sin filtros).",
)
async def listar_estregcontablepagos(
):
    try:
        items = await EstRegContablePagosService.listar()
        return _to_api_response(items)
    except CustomException as ce:
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado listando estregcontablepagos: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener cartera")


@router.get(
    "/estregcontablepagos/{anio}",
    response_model=EstRegContablePagosApiResponse,
    summary="Listado por año",
    description="Filtra por año de `femisi` (fecha de emisión).",
)
async def listar_estregcontablepagos_anio(
    anio: int = Path(..., ge=1900, le=2100),
):
    try:
        items = await EstRegContablePagosService.listar(anio=anio)
        return _to_api_response(items)
    except CustomException as ce:
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)


@router.get(
    "/estregcontablepagos/{anio}/{mes}",
    response_model=EstRegContablePagosApiResponse,
    summary="Listado por año y mes",
    description="Filtra por año y mes de `femisi` (fecha de emisión).",
)
async def listar_estregcontablepagos_anio_mes(
    anio: int = Path(..., ge=1900, le=2100),
    mes: int = Path(..., ge=1, le=12),
):
    try:
        items = await EstRegContablePagosService.listar(anio=anio, mes=mes)
        return _to_api_response(items)
    except CustomException as ce:
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)


@router.get(
    "/estregcontablepagos/{campana}/{valor}",
    response_model=EstRegContablePagosApiResponse,
    summary="Listado por campaña y tipo_documento o fecha",
    description=(
        "Por limitaciones de ruteo (dos rutas idénticas `/{campana}/{x}`), este endpoint acepta `valor` como:\n"
        "- `tipo_documento` (ej: '01', 'FT')\n"
        "- o `fecha` en formato YYYY-MM-DD (ej: '2026-04-06')\n"
        "y aplica el filtro correspondiente."
    ),
)
async def listar_estregcontablepagos_campana_valor(
    campana: str = Path(..., min_length=1, max_length=7),
    valor: str = Path(..., min_length=1, max_length=50),
):
    try:
        valor_stripped = valor.strip()
        fecha: Optional[date] = None
        tipo_documento: Optional[str] = None

        try:
            fecha = date.fromisoformat(valor_stripped)
        except ValueError:
            tipo_documento = valor_stripped

        items = await EstRegContablePagosService.listar(
            campana=campana,
            tipo_documento=tipo_documento,
            fecha=fecha,
        )
        return _to_api_response(items)

    except ValidationError as ve:
        raise HTTPException(status_code=ve.status_code, detail=ve.detail)
    except CustomException as ce:
        raise HTTPException(status_code=ce.status_code, detail=ce.detail)
    except Exception as e:
        logger.exception(f"Error inesperado listando estregcontablepagos por campaña: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener cartera")
