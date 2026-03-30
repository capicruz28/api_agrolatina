from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AvisoApItem(BaseModel):
    """Aviso general de aceptación (ctpref='AP') asociado a un trabajador."""

    ctraba: str = Field(..., description="Código del trabajador (ctraba)")
    saprob: str = Field(..., description="Estado de aprobación: N=Pendiente, S=Aceptado")
    faprob: Optional[datetime] = Field(None, description="Fecha/hora de aceptación (faprob)")
    fvisual: Optional[datetime] = Field(None, description="Fecha/hora de visualización (fvisual)")

    archivo_pdf_base64: str = Field(..., description="Archivo PDF en formato base64")
    nombre_archivo: str = Field(..., description="Nombre sugerido para el archivo")


class AvisoApPendienteResponse(BaseModel):
    """Respuesta para validar si existe un aviso AP pendiente al iniciar sesión."""

    pendiente: bool = Field(..., description="Indica si existe aviso pendiente")
    aviso: Optional[AvisoApItem] = Field(None, description="Detalle del aviso cuando pendiente=true")


class AvisoApVisualizadoResponse(BaseModel):
    """Respuesta de la acción 'marcar visualizado'."""

    rows_affected: int = Field(..., description="Filas afectadas en la actualización")
    fvisual: Optional[datetime] = Field(None, description="Fecha/hora visualizada resultante")


class AvisoApAceptarRequest(BaseModel):
    """Request para aceptar el aviso AP (conforme)."""

    conforme: bool = Field(..., description="Debe ser true para aceptar el aviso")


class AvisoApAceptarResponse(BaseModel):
    """Respuesta de la acción 'aceptar aviso'."""

    rows_affected: int = Field(..., description="Filas afectadas en la actualización")
    saprob: Optional[str] = Field(None, description="Estado final (esperado 'S')")
    faprob: Optional[datetime] = Field(None, description="Fecha/hora de aceptación resultante")

