import json
import socket
import threading
import time

import pytest

from ocarina_beat.servidor import Servidor

CANCAO = {
    "id": "teste", "nome": "Teste", "reconhecer_primeiras": 4,
    "notes": [{"midi": m, "beats": b} for m, b in [(74, 1), (77, 1), (79, 2), (77, 1), (74, 1)]],
}


@pytest.fixture
def ambiente(monkeypatch):
    # simulação sem esperar o relógio: o teste não precisa de tempo real
    monkeypatch.setattr("ocarina_beat.fontes.em_tempo_real", lambda fs, blocos: blocos)
    ouvinte = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ouvinte.bind(("127.0.0.1", 0))
    ouvinte.settimeout(0.2)
    s = Servidor([CANCAO], porta_eventos=ouvinte.getsockname()[1], porta_comandos=0)
    th = threading.Thread(target=s.executar, kwargs={"max_s": 10}, daemon=True)
    th.start()
    yield s, ouvinte
    s.ativo = False
    th.join(2)
    s.fechar()
    ouvinte.close()


def comandar(s, **msg):
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.sendto(json.dumps(msg).encode(), ("127.0.0.1", s.porta_comandos))
    c.close()


def coletar(ouvinte, ate, limite_s=8):
    """Lê mensagens até uma satisfazer `ate` (ou estourar o tempo)."""
    msgs, fim = [], time.time() + limite_s
    while time.time() < fim:
        try:
            m = json.loads(ouvinte.recv(65535))
        except socket.timeout:
            continue
        msgs.append(m)
        if ate(m):
            break
    return msgs


def test_estado_inicial(ambiente):
    s, o = ambiente
    m = coletar(o, lambda m: m["tipo"] == "estado")[-1]
    assert m["modo"] == "livre" and m["ouvindo"] is False


def test_lista_de_cancoes(ambiente):
    s, o = ambiente
    comandar(s, cmd="cancoes")
    m = coletar(o, lambda m: m["tipo"] == "cancoes")[-1]
    assert m["lista"][0]["id"] == "teste" and m["lista"][0]["notas"][0] == "D5"


def test_simular_no_modo_livre_reconhece(ambiente):
    s, o = ambiente
    comandar(s, cmd="simular", id="teste", bpm=100)
    msgs = coletar(o, lambda m: m["tipo"] == "fim_audio")
    tipos = [m["tipo"] for m in msgs]
    assert "reconhecida" in tipos and "nota" in tipos and "nivel" in tipos
    assert [m for m in msgs if m["tipo"] == "reconhecida"][0]["id"] == "teste"


def test_simular_no_modo_aprender_completa(ambiente):
    s, o = ambiente
    comandar(s, cmd="aprender", id="teste")
    comandar(s, cmd="simular", id="teste")
    msgs = coletar(o, lambda m: m["tipo"] == "fim_audio")
    assert "completa" in [m["tipo"] for m in msgs]
    comandar(s, cmd="estado")
    est = coletar(o, lambda m: m["tipo"] == "estado" and m["aprendidas"])[-1]
    assert est["aprendidas"] == ["teste"]


def test_comando_invalido_nao_derruba(ambiente):
    s, o = ambiente
    comandar(s, cmd="voar")
    comandar(s, cmd="aprender", id="nao_existe")
    erros = [m for m in coletar(o, lambda m: False, limite_s=1.0) if m["tipo"] == "erro"]
    assert len(erros) == 2
    comandar(s, cmd="estado")
    assert coletar(o, lambda m: m["tipo"] == "estado")
