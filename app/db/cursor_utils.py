# app/db/cursor_utils.py
"""Lectura eficiente desde pyodbc: arraysize + fetchmany (evita fetchall lento por lotes de 1 fila)."""
from __future__ import annotations

from typing import Any, Dict, List

import pyodbc


def fetch_all_dicts(cursor: pyodbc.Cursor, batch_size: int = 4000) -> List[Dict[str, Any]]:
    """
    Convierte todas las filas del cursor actual en diccionarios.
    Usa fetchmany + arraysize alto: con el default de pyodbc cada fetch puede ir fila a fila.
    """
    if cursor.description is None:
        return []
    columns = tuple(col[0] for col in cursor.description)
    cursor.arraysize = batch_size
    out: List[Dict[str, Any]] = []
    while True:
        chunk = cursor.fetchmany(batch_size)
        if not chunk:
            break
        out.extend(dict(zip(columns, row)) for row in chunk)
    return out
