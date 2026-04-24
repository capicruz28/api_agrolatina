from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EstRegContablePagosItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    ruc: Optional[str] = Field(default=None, alias="RUC")
    codigo: Optional[str] = None
    proveedor: Optional[str] = None
    direccion: Optional[str] = None
    cuenta_bancaria: Optional[str] = None
    estado: Optional[str] = None

    tipo_documento: Optional[str] = None
    descripcion_documento: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None

    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None

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
    centro_costos: Optional[str] = None
    gasto: Optional[str] = None
    fundo: Optional[str] = None


class EstRegContablePagosApiResponse(BaseModel):
    """Formato estándar para consumo del cliente."""

    error: int = 0
    total: int
    mensaje: str = "Datos Obtenidos Correctamente"
    status: str = "ok"
    results: List[EstRegContablePagosItem]
