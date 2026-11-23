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
    tocados = []
    s = Servidor([CANCAO], porta_eventos=ouvinte.getsockname()[1], porta_comandos=0,
                 tocador=lambda x, fs: tocados.append(len(x) / fs))
    s.tocados = tocados
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


def test_ouvir_toca_referencia_e_marca_as_notas(ambiente):
    s, o = ambiente
    comandar(s, cmd="ouvir", id="teste", bpm=240)
    msgs = coletar(o, lambda m: m["tipo"] == "audio_fim")
    inicio = [m for m in msgs if m["tipo"] == "audio_inicio"]
    assert inicio and inicio[0]["som"] == "referencia"
    refs = [m for m in msgs if m["tipo"] == "referencia"]
    assert [m["indice"] for m in refs] == [0, 1, 2, 3, 4] and refs[0]["nome"] == "D5"
    assert len(s.tocados) == 1


def test_livre_toca_a_cancao_reconhecida(ambiente):
    s, o = ambiente
    comandar(s, cmd="simular", id="teste")
    msgs = coletar(o, lambda m: m["tipo"] == "fim_audio")
    inicios = [m for m in msgs if m["tipo"] == "audio_inicio"]
    assert inicios and inicios[0]["som"] == "cancao"  # modo livre toca a canção reconhecida


def test_completa_toca_sucesso(ambiente):
    s, o = ambiente
    comandar(s, cmd="aprender", id="teste")
    comandar(s, cmd="simular", id="teste")
    msgs = coletar(o, lambda m: m["tipo"] == "audio_inicio")
    assert msgs[-1]["som"] == "sucesso"


def test_microfone_fica_mudo_durante_o_som(ambiente):
    import numpy as np

    from ocarina_beat import audio as au

    s, o = ambiente
    s.ativo = False  # para o laço; vamos chamar _passo na mão
    time.sleep(0.05)
    tom = au.nota(74, 1.0)
    s._iniciar_fonte(au.FS, iter([tom[i:i + 512] for i in range(0, len(tom), 512)]), ao_vivo=True)
    s._mudo_ate = time.time() + 60
    for _ in range(80):
        s._passo()
    assert s.proc.notas == []  # nada passou enquanto o jogo tocava
    assert all(q.midi is None for q in s.proc.quadros)
    assert np.isfinite(s.proc.tempo)
