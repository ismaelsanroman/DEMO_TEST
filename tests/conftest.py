# tests/conftest.py

import sys
import os
import pytest
import httpx
import allure
import shutil

import log_config
from loguru import logger


# Redirige stdout/stderr SOLO durante el test, no de forma global
class StreamToLogger:
    def __init__(self, level):
        self.level = level

    def write(self, message):
        if message.strip():
            for line in message.rstrip().splitlines():
                logger.log(self.level, line.rstrip())

    def flush(self):
        pass


# Inyectamos la carpeta raíz para importar bien
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MICROS = {
    "orquestador": "http://localhost:8000",
    "consultas": "http://localhost:8001",
    "cuentas": "http://localhost:8002",
    "identidad": "http://localhost:8003",
    "ia": "http://localhost:8004",
}


@pytest.fixture(scope="session")
def api_client():
    client = httpx.Client()
    yield client
    client.close()


@pytest.fixture
def record_api_call(api_client):
    def _call(method: str, path: str, **kwargs):
        base = MICROS.get(path.lstrip("/").split("/")[0], "")
        url = base + path
        with allure.step(f"{method.upper()} {url}"):
            resp = api_client.request(method, url, **kwargs)
            allure.attach(
                f"{resp.request.method} {resp.request.url}\n\n"
                f"{(resp.request.content or b'').decode(errors='ignore')}",
                name="Petición",
                attachment_type=allure.attachment_type.TEXT
            )
            allure.attach(
                f"{resp.status_code}\n\n{resp.text}",
                name="Respuesta",
                attachment_type=allure.attachment_type.JSON
            )
        return resp

    return _call


@pytest.fixture(scope="session", autouse=True)
def allure_environment():
    env = {k.upper(): v for k, v in MICROS.items()}
    props = "\n".join(f"{k}={v}" for k, v in env.items())
    out_dir = os.getenv("ALLURE_RESULTS_DIR", "reports/unit_results")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "environment.properties"), "w") as f:
        f.write(props)


@pytest.fixture(scope="session")
def token(api_client):
    resp = api_client.post(f"{MICROS['orquestador']}/token")
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.fixture
def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# Logging automático en cada test
@pytest.fixture(autouse=True)
def log_test_info(request):
    # Redirige stdout/stderr temporalmente
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = StreamToLogger("INFO")
    sys.stderr = StreamToLogger("ERROR")

    logger.info(f"[test] 🧪 Inicio: {request.node.nodeid}")
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        logger.error(f"[test] ❌ Falló: {request.node.nodeid}")
    else:
        logger.success(f"[test] ✅ OK: {request.node.nodeid}")

    sys.stdout = old_stdout
    sys.stderr = old_stderr


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    try:
        from log_config import get_log_file
        log_path = get_log_file()
        allure_dir = os.getenv("ALLURE_RESULTS_DIR", "reports/unit_results")
        os.makedirs(allure_dir, exist_ok=True)
        dest_path = os.path.join(allure_dir, os.path.basename(log_path))

        shutil.copy(log_path, dest_path)
        logger.info(f"[log] 📝 Log adjuntado a Allure: {dest_path}")
    except Exception as e:
        # No usamos logger aquí por si el sink ya está cerrado
        print(f"[log] ❌ Error al copiar log a Allure: {e}")
