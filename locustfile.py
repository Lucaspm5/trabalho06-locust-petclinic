"""
Trabalho 06 - Avaliacao de desempenho do Spring PetClinic Microservices.

Perfis (escolhidos pelo nome da classe na linha de comando):
  ReadProfileUser  -> 45% GET /owners | 35% GET /owners/{id} | 15% GET /vets | 5% POST /owners
  WriteProfileUser -> 20% GET /owners | 20% GET /owners/{id} | 20% GET /vets | 40% POST /owners

Todas as requisicoes passam pelo API Gateway (porta 8080):
  /api/customer/owners... -> customers-service
  /api/vet/vets           -> vets-service

Se a variavel de ambiente RAW_CSV estiver definida, cada requisicao e gravada
nesse arquivo; o analyze.py usa esse log para descartar o aquecimento e calcular
media e P95 exatos da janela medida.
"""
import csv
import os
import random
import string
import time

from locust import HttpUser, between, events

CUSTOMER_API = "/api/customer"
VET_API = "/api/vet"
OWNER_IDS = list(range(1, 11))  # 10 owners carregados no startup (HSQLDB)

RAW_CSV = os.getenv("RAW_CSV")
_raw = {"fh": None, "writer": None, "t0": 0.0}


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    _raw["t0"] = time.time()
    if RAW_CSV:
        os.makedirs(os.path.dirname(os.path.abspath(RAW_CSV)), exist_ok=True)
        _raw["fh"] = open(RAW_CSV, "w", newline="")
        _raw["writer"] = csv.writer(_raw["fh"])
        _raw["writer"].writerow(
            ["timestamp", "t_rel", "method", "name", "response_time_ms", "success", "status", "error"]
        )


@events.request.add_listener
def _on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    writer = _raw["writer"]
    if writer is None:
        return
    now = time.time()
    status = response.status_code if response is not None else 0
    error = str(exception)[:80] if exception else ""
    writer.writerow([
        f"{now:.3f}", f"{now - _raw['t0']:.3f}", request_type, name,
        f"{response_time:.2f}", 0 if exception else 1, status, error,
    ])


@events.test_stop.add_listener
def _on_test_stop(environment, **kwargs):
    if _raw["fh"]:
        _raw["fh"].flush()
        _raw["fh"].close()
        _raw["fh"] = None
        _raw["writer"] = None


def _check(resp, expected):
    if resp.status_code in expected:
        resp.success()
    else:
        resp.failure(f"HTTP {resp.status_code}")


def get_owners(user):
    with user.client.get(f"{CUSTOMER_API}/owners", name="GET /owners", catch_response=True) as resp:
        _check(resp, (200,))


def get_owner(user):
    owner_id = random.choice(OWNER_IDS)
    with user.client.get(f"{CUSTOMER_API}/owners/{owner_id}", name="GET /owners/{id}", catch_response=True) as resp:
        _check(resp, (200,))


def get_vets(user):
    with user.client.get(f"{VET_API}/vets", name="GET /vets", catch_response=True) as resp:
        _check(resp, (200,))


def post_owner(user):
    suffix = "".join(random.choices(string.ascii_lowercase, k=8))
    payload = {
        "firstName": "Load",
        "lastName": f"Test{suffix}",
        "address": "110 W. Liberty St.",
        "city": "Madison",
        "telephone": "".join(random.choices(string.digits, k=10)),
    }
    with user.client.post(f"{CUSTOMER_API}/owners", json=payload, name="POST /owners", catch_response=True) as resp:
        _check(resp, (200, 201))


class ReadProfileUser(HttpUser):
    """Perfil 1 - Leitura."""
    wait_time = between(1, 2)
    tasks = {get_owners: 45, get_owner: 35, get_vets: 15, post_owner: 5}


class WriteProfileUser(HttpUser):
    """Perfil 2 - Escrita."""
    wait_time = between(1, 2)
    tasks = {get_owners: 20, get_owner: 20, get_vets: 20, post_owner: 40}
