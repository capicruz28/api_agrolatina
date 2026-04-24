# app/db/cartera_db.py
"""Ejecución optimizada del SP de cartera (pool + fetchmany)."""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings
from app.db.cursor_utils import fetch_all_dicts
from app.db.pool import get_cartera_pool

_PROCEDURE = "dbo.sp_api_agrolatina_cartera_nuevo"


def execute_sp_api_agrolatina_cartera_nuevo(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    param_str = ", ".join(f"@{key} = ?" for key in params.keys())
    sql = f"EXEC {_PROCEDURE} {param_str}"
    batch = max(500, int(settings.DB_CARTERA_FETCH_BATCH))
    pool = get_cartera_pool()
    with pool.connection() as conn:
        cur = conn.cursor()
        try:
            cur.arraysize = batch
            cur.execute(sql, tuple(params.values()))
            results: List[Dict[str, Any]] = []
            while True:
                if cur.description:
                    results.extend(fetch_all_dicts(cur, batch_size=batch))
                if not cur.nextset():
                    break
            return results
        finally:
            cur.close()
