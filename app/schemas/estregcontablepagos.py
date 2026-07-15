from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _coerce_optional_date_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


class PagoDetalleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pago: Optional[float] = None
    fecha_pago: Optional[str] = None

    @field_validator("fecha_pago", mode="before")
    @classmethod
    def coerce_fecha_pago(cls, value: object) -> str | None:
        return _coerce_optional_date_str(value)

class EstRegContablePagosItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    ruc: Optional[str] = Field(default=None, alias="RUC")
    codigo: Optional[str] = None
    proveedor: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    cuenta_bancaria: Optional[str] = None
    estado: Optional[str] = None

    tipo_documento: Optional[str] = None
    descripcion_documento: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None

    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    fecha_registro: Optional[str] = None
    codigo_moneda: Optional[str] = None
    moneda: Optional[str] = None
    importe: Optional[Decimal] = None
    saldo: Optional[Decimal] = None

    oc: Optional[str] = Field(default=None, alias="OC")
    fecha_detraccion: Optional[str] = None
    monto_detraccion: Optional[Decimal] = None
    fecha_retencion: Optional[str] = None
    monto_retencion: Optional[Decimal] = None
    planilla_compra: Optional[str] = None

    campanna: Optional[str] = None
    descripcion_campanna: Optional[str] = None
    centro_costos: Optional[str] = None
    descripcion_centro_costos: Optional[str] = None
    cultivo: Optional[str] = None
    descripcion_cultivo: Optional[str] = None
    glosa_cabecera: Optional[str] = None
    glosa_detalle: Optional[str] = None

    detalle_pagos: List[PagoDetalleResponse] = []


class EstRegContablePagosApiResponse(BaseModel):
    """Formato estándar para consumo del cliente."""

    error: int = 0
    total: int
    mensaje: str = "Datos Obtenidos Correctamente"
    status: str = "ok"
    results: List[EstRegContablePagosItem]
