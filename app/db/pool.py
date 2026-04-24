# app/db/pool.py
"""Pool acotado de conexiones pyodbc (reutiliza conexiones y evita conectar en cada request)."""
from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from typing import Callable, Iterator

import pyodbc

from app.core.config import settings
from app.core.exceptions import DatabaseError
from app.db.connection import DatabaseConnection, get_connection_string

PoolFactory = Callable[[], pyodbc.Connection]


def _ping(conn: pyodbc.Connection) -> bool:
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        return True
    except Exception:
        return False
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass


class BoundedPyODBCPool:
    """
    Máximo `size` conexiones concurrentes; las devueltas se reutilizan.
    """

    def __init__(self, connect_fn: PoolFactory, size: int):
        self._connect = connect_fn
        self._size = max(1, size)
        self._sem = threading.BoundedSemaphore(self._size)
        self._idle: queue.Queue[pyodbc.Connection] = queue.Queue(maxsize=self._size)

    @contextmanager
    def connection(self) -> Iterator[pyodbc.Connection]:
        self._sem.acquire()
        conn: pyodbc.Connection | None = None
        ok_put_back = False
        try:
            try:
                conn = self._idle.get_nowait()
            except queue.Empty:
                conn = self._connect()

            if not _ping(conn):
                try:
                    conn.close()
                except Exception:
                    pass
                conn = self._connect()

            conn.autocommit = True
            yield conn
            ok_put_back = True
        except pyodbc.Error as e:
            ok_put_back = False
            raise DatabaseError(detail=f"Error de base de datos: {str(e)}")
        except BaseException:
            ok_put_back = False
            raise
        finally:
            try:
                if conn is not None and ok_put_back:
                    try:
                        self._idle.put_nowait(conn)
                    except queue.Full:
                        conn.close()
                elif conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            finally:
                self._sem.release()


_CARTERA_POOL: BoundedPyODBCPool | None = None
_CARTERA_POOL_LOCK = threading.Lock()


def _connect_default_readonly() -> pyodbc.Connection:
    conn_str = get_connection_string(DatabaseConnection.DEFAULT)
    timeout = max(5, settings.DB_CONN_TIMEOUT_SECONDS)
    return pyodbc.connect(conn_str, timeout=timeout)


def get_cartera_pool() -> BoundedPyODBCPool:
    global _CARTERA_POOL
    with _CARTERA_POOL_LOCK:
        if _CARTERA_POOL is None:
            size = max(1, settings.DB_POOL_SIZE)
            _CARTERA_POOL = BoundedPyODBCPool(_connect_default_readonly, size)
        return _CARTERA_POOL
