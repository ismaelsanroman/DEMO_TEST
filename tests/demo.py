import pytest
from fastapi import HTTPException

# Importar las funciones/módulos reales.  Ajusta la ruta si tu módulo no se llama exactly ``regards``.
# Para los type‑checkers / linters que no tengan instalado tu paquete en el entorno del CI,
# añadimos ``type: ignore``.
from regards import (
    get_current_user,          # type: ignore
    list_sessions,             # type: ignore
    session_status,            # type: ignore
    end_session,               # type: ignore
    create_new_runtime,        # type: ignore
    list_runtimes,             # type: ignore
)

####################################################################################################
# UTILIDADES de test – mocks MUY ligeros  ***********************************************************
####################################################################################################

class _DummyQuery:
    """Simula un objeto ``Query`` de SQLAlchemy pero sin la base de datos."""

    def __init__(self, seq):
        self._seq = seq

    # La API de *chaining* admite ``.filter(...).all()`` y ``.filter(...).first()``
    def filter(self, *_, **__):  # noqa: D401,E501  – aceptamos lo que sea y devolvemos self
        return self

    def all(self):
        return self._seq

    def first(self):
        return self._seq[0] if self._seq else None


class _DummyDB:
    """Base ultra‑sencilla para parchar el parámetro ``db`` de las dependencias."""

    def __init__(self, query_result):
        self._result = query_result
        self.committed = False
        self.rolled_back = False

    # ``regards`` hace ``db.query(Model).filter(...).all()`` / ``first()``
    def query(self, *_, **__):  # noqa: D401,E501
        return _DummyQuery(self._result)

    # Métodos de transacción para comprobar efectos laterales
    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def delete(self, _obj):  # pragma: no cover – no necesitamos lógica
        pass

    def add(self, _obj):  # pragma: no cover
        pass


####################################################################################################
# TESTS  *******************************************************************************************
####################################################################################################

# --------------------------------------------------------------------------------------------------
# 1) AUTENTICACIÓN *********************************************************************************
# --------------------------------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.auth
def test_get_current_user_valido_retorna_usuario():
    """Un token válido debe devolver el identificador de usuario correspondiente."""
    assert get_current_user("token_user_demo") == "user_demo"  # noqa: S101 – aserción directa


@pytest.mark.unit
@pytest.mark.auth
def test_get_current_user_token_invalido_lanza_401():
    """Con un token inválido se debe lanzar una *HTTPException* 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user("token_malo")

    exc = exc_info.value
    assert exc.status_code == 401
    assert "Token no válido" in str(exc.detail)


# --------------------------------------------------------------------------------------------------
# 2) LISTA DE SESIONES ******************************************************************************
# --------------------------------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.sessions
def test_list_sessions_sin_sesiones_devuelve_lista_vacia(monkeypatch):
    """Si el usuario no tiene sesiones activas, se devuelve una lista vacía."""
    db = _DummyDB(query_result=[])

    lista = list_sessions(db=db, current_user="user_demo")  # type: ignore[arg-type]
    assert lista == []


@pytest.mark.unit
@pytest.mark.sessions
def test_list_sessions_devuelve_sesiones_activas(monkeypatch):
    """Comprueba que se mapean correctamente los campos de las sesiones."""

    class _SessionRecord:
        def __init__(self, sid, runtime_sid, user_id):
            self.id = sid
            self.runtime_session_id = runtime_sid
            self.user_id = user_id

    dummy_records = [
        _SessionRecord("S‑1", "R‑1", "user_demo"),
        _SessionRecord("S‑2", "R‑2", "user_demo"),
    ]

    db = _DummyDB(query_result=dummy_records)

    result = list_sessions(db=db, current_user="user_demo")  # type: ignore[arg-type]

    assert result == [
        {"id": "S‑1", "runtime_session_id": "R‑1", "status": "active", "user_id": "user_demo"},
        {"id": "S‑2", "runtime_session_id": "R‑2", "status": "active", "user_id": "user_demo"},
    ]


# --------------------------------------------------------------------------------------------------
# 3) ESTADO DE SESIÓN ******************************************************************************
# --------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.sessions
async def test_session_status_sesion_no_encontrada(monkeypatch):
    """Debe levantarse 404 si la sesión solicitada no existe."""
    db = _DummyDB(query_result=[])  # ``first()`` devolverá None -> provoca 404

    with pytest.raises(HTTPException) as exc_info:
        await session_status(session_id="S‑404", db=db, current_user="user_demo")  # type: ignore[arg-type]

    assert exc_info.value.status_code == 404


# --------------------------------------------------------------------------------------------------
# 4) CREACIÓN DE RUNTIME **************************************************************************
# --------------------------------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.runtime
def test_create_new_runtime_error_propagado(monkeypatch):
    """Simula que la función auxiliar lanza excepción → se debe propagar como 500."""

    def _boom():  # noqa: D401 – función que siempre explota
        raise RuntimeError("no kube :(")

    monkeypatch.setattr("regards.create_runtime_pod", _boom)  # type: ignore[attr-defined]

    with pytest.raises(HTTPException) as exc_info:
        create_new_runtime(db=_DummyDB([]), current_user="user_demo")  # type: ignore[arg-type]

    assert exc_info.value.status_code == 500
    assert "crear runtime" in str(exc_info.value.detail)


# --------------------------------------------------------------------------------------------------
# 5) LISTAR RUNTIMES *******************************************************************************
# --------------------------------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.runtime
def test_list_runtimes_sin_registros(monkeypatch):
    """Con cero runtimes en BBDD, el endpoint responde con lista vacía."""
    db = _DummyDB(query_result=[])

    result = list_runtimes(db=db, current_user="user_demo")  # type: ignore[arg-type]
    assert result == []

