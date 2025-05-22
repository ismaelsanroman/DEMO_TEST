import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from types import SimpleNamespace

# 🗂️ Importamos la app FastAPI y el módulo que contiene la lógica
from src.app.main import app  # type: ignore
from src.resources import regards as regards_mod  # type: ignore

###############################################################################
# Utilidades de prueba (dobles y fakes)
###############################################################################

class _FakeQuery:  # imita ``session.query(...).filter(...).first()`` / ``all()``
    def __init__(self, result):
        self._result = result

    def filter(self, *_, **__):  # noqa: D401, ANN001 – fake
        return self

    def all(self):
        return self._result if isinstance(self._result, list) else [self._result]

    def first(self):
        # Devuelve sólo el primero o None
        if isinstance(self._result, list):
            return self._result[0] if self._result else None
        return self._result

class _FakeDB:  # fake mínimo de SQLAlchemy Session
    def __init__(self, result=None):
        self._result = result or []

    # ``query(Model)`` devuelve un FakeQuery ya preparado
    def query(self, *_):  # noqa: D401 – simplicity
        return _FakeQuery(self._result)

    def add(self, *_):
        pass

    def commit(self):
        pass

    def rollback(self):  # noqa: D401
        pass

###############################################################################
# Overrides globales para la app (get_db & get_current_user)
###############################################################################

def _override_get_db_empty():
    return _FakeDB([])

def _override_get_current_user():  # always returns "user_demo"
    return "user_demo"

app.dependency_overrides[regards_mod.get_db] = _override_get_db_empty  # type: ignore[attr-defined]
app.dependency_overrides[regards_mod.get_current_user] = _override_get_current_user  # type: ignore[attr-defined]

client = TestClient(app)

###############################################################################
# 🧪 Tests
###############################################################################

# ---------------------------------------------------------------------------
# Auth – get_current_user ----------------------------------------------------
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.new_tests
#allure.feature("Regards API")
#allure.story("Auth – invalid token")
def test_get_current_user_invalid_token():
    """Un token no válido debe disparar HTTPException 401."""
    with pytest.raises(HTTPException) as exc:
        regards_mod.get_current_user("bad-token")  # type: ignore[arg-type]
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

# ---------------------------------------------------------------------------
# /login ---------------------------------------------------------------------
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.success
@pytest.mark.new_tests
#allure.feature("Regards API")
#allure.story("Login – success")
def test_login_success():
    """Login con credenciales correctas devuelve un token."""
    resp = client.post("/login", json={"username": "user_demo", "password": "secret"})
    assert resp.status_code == 200
    assert resp.json() == {"token": "token_user_demo"}

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.error
@pytest.mark.new_tests
#allure.feature("Regards API")
#allure.story("Login – failure")
def test_login_failure():
    """Login con credenciales erróneas devuelve 401."""
    resp = client.post("/login", json={"username": "wrong", "password": "bad"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

# ---------------------------------------------------------------------------
# list_sessions --------------------------------------------------------------
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.sessions
@pytest.mark.success
#allure.feature("Regards API")
#allure.story("List sessions – empty")
def test_list_sessions_empty(monkeypatch):
    """Cuando un usuario no tiene sesiones, se devuelve lista vacía."""
    monkeypatch.setattr(regards_mod, "SessionRecord", SimpleNamespace)  # type: ignore[attr-defined]
    fake_db = _FakeDB([])
    result = regards_mod.list_sessions(db=fake_db, current_user="user_demo")  # type: ignore
    assert result == []

# ---------------------------------------------------------------------------
# create_new_runtime ---------------------------------------------------------
# ---------------------------------------------------------------------------

class _FakeRuntimeRec(SimpleNamespace):
    pass

@pytest.mark.unit
@pytest.mark.runtime
@pytest.mark.success
#allure.feature("Runtime management")
#allure.story("Create runtime – success")
def test_create_new_runtime_success(monkeypatch):
    """Debe devolver dict con info del runtime."""

    fake_runtime = _FakeRuntimeRec(runtime_id="rt-123", endpoint="http://rt", status="available")
    monkeypatch.setattr(regards_mod, "create_runtime_pod", lambda: fake_runtime, raising=True)  # type: ignore[attr-defined]

    result = regards_mod.create_new_runtime(db=_FakeDB([]), current_user="user_demo")  # type: ignore

    assert result == {
        "runtime_id": "rt-123",
        "endpoint": "http://rt",
        "status": "available",
    }

@pytest.mark.unit
@pytest.mark.runtime
@pytest.mark.error
#allure.feature("Runtime management")
#allure.story("Create runtime – error")
def test_create_new_runtime_error_propagated(monkeypatch):
    """Si create_runtime_pod lanza excepción, debe salir HTTPException 500."""

    def _boom():
        raise RuntimeError("no kube :(")

    monkeypatch.setattr(regards_mod, "create_runtime_pod", _boom, raising=True)  # type: ignore[attr-defined]

    with pytest.raises(HTTPException) as exc:
        regards_mod.create_new_runtime(db=_FakeDB([]), current_user="user_demo")  # type: ignore

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

# ---------------------------------------------------------------------------
# list_runtimes --------------------------------------------------------------
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.runtime
@pytest.mark.success
#allure.feature("Runtime management")
#allure.story("List runtimes – empty")
def test_list_runtimes_empty():
    """Si no hay runtimes, devuelve lista vacía."""
    result = regards_mod.list_runtimes(db=_FakeDB([]), current_user="user_demo")  # type: ignore
    assert result == []

@pytest.mark.unit
@pytest.mark.runtime
@pytest.mark.success
#allure.feature("Runtime management")
#allure.story("List runtimes – populated")
def test_list_runtimes_populated():
    """Devuelve lista con info de cada runtime cuando existen."""
    fake_r = SimpleNamespace(runtime_id="rt-1", status="occupied", session_id="sess-1", user_id="user_demo", endpoint="http://rt")
    result = regards_mod.list_runtimes(db=_FakeDB([fake_r]), current_user="user_demo")  # type: ignore
    assert result == [
        {
            "runtime_id": "rt-1",
            "status": "occupied",
            "session_id": "sess-1",
            "user_id": "user_demo",
            "endpoint": "http://rt",
        }
    ]
